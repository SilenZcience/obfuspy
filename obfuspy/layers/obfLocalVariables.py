import ast

from obfuspy.util.randomizer import Randomizer


class ObfLocalVariables(ast.NodeTransformer): # TODO: verify
    """
    Obfuscates local variables in function scopes (including nested ones).
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.current_table_stack = []
        self.local_var_map_stack = []
        # Caches for performance
        self._cached_child_table = {}
        self._cached_resolved_names = {}

    def _lookup_symbol(self, table, name: str):
        if table is None:
            return None
        try:
            return table.lookup(name)
        except KeyError:
            return None

    def _child_table_for(self, node):
        # Use cache to avoid repeated lookups for the same node in the same parent table
        current_table = self.current_table_stack[-1] if self.current_table_stack else None
        cache_key = (id(current_table), id(node))
        cache = self._cached_child_table
        if cache_key in cache:
            return cache[cache_key]
        if current_table is None:
            cache[cache_key] = None
            return None

        node_name = 'lambda' if isinstance(node, ast.Lambda) else getattr(node, 'name', None)
        node_lineno = getattr(node, 'lineno', None)

        expected_type = 'class' if isinstance(node, ast.ClassDef) else 'function'
        typed_children = [child for child in current_table.get_children() if child.get_type() == expected_type]

        result = None
        if node_lineno is not None:
            line_matches = [child for child in typed_children if child.get_lineno() == node_lineno]
            if len(line_matches) == 1:
                result = line_matches[0]
            elif line_matches and node_name is not None:
                for child in line_matches:
                    if child.get_name() == node_name:
                        result = child
                        break
                if result is None:
                    result = line_matches[0]

        if result is None and node_name is not None:
            for child in typed_children:
                if child.get_name() == node_name:
                    result = child
                    break

        if result is None and typed_children:
            result = typed_children[0]

        cache[cache_key] = result
        return result

    def _build_local_var_map(self, table) -> dict:
        if table is None or table.get_type() != 'function':
            return {}

        local_var_map = {}
        for symbol in table.get_symbols():
            if symbol.is_parameter() or symbol.is_imported():
                continue
            if not symbol.is_local():
                continue
            if hasattr(symbol, 'is_namespace') and symbol.is_namespace():
                continue

            local_var_map[symbol.get_name()] = next(self.randomizer.random_name_gen)

        return local_var_map

    def _in_function_scope(self) -> bool:
        return bool(self.current_table_stack) and self.current_table_stack[-1].get_type() == 'function'

    def _resolve_renamed_name(self, name: str):
        # Use cache to avoid repeated resolution in the same scope stack
        cache_key = (tuple(id(t) for t in self.current_table_stack), name)
        cache = self._cached_resolved_names
        if cache_key in cache:
            return cache[cache_key]
        # Resolve lexical names from inner to outer scope.
        for idx in range(len(self.current_table_stack) - 1, -1, -1):
            table = self.current_table_stack[idx]
            symbol = self._lookup_symbol(table, name)
            if symbol is None:
                continue

            if symbol.is_global() or symbol.is_imported() or symbol.is_parameter():
                cache[cache_key] = None
                return None

            if symbol.is_local():
                result = self.local_var_map_stack[idx].get(name)
                cache[cache_key] = result
                return result

            if symbol.is_free() or symbol.is_nonlocal():
                continue

            cache[cache_key] = None
            return None

        cache[cache_key] = None
        return None
    def _invalidate_caches(self):
        self._cached_child_table.clear()
        self._cached_resolved_names.clear()

    def visit_Module(self, node):
        self.current_table_stack = [self.file_module.symtable]
        self.local_var_map_stack = [{}]
        self._invalidate_caches()
        self.generic_visit(node)
        self.local_var_map_stack.pop()
        self.current_table_stack.pop()
        self._invalidate_caches()
        return node

    def visit_ClassDef(self, node):
        child_table = self._child_table_for(node)
        if child_table is not None:
            self.current_table_stack.append(child_table)
            self.local_var_map_stack.append({})
            self._invalidate_caches()

        self.generic_visit(node)

        if child_table is not None:
            self.local_var_map_stack.pop()
            self.current_table_stack.pop()
            self._invalidate_caches()
        return node

    def _visit_callable(self, node):
        if isinstance(node, ast.Lambda):
            self.visit(node.args)
        else:
            for deco in node.decorator_list:
                self.visit(deco)
            self.visit(node.args)
            if node.returns:
                self.visit(node.returns)

        child_table = self._child_table_for(node)
        local_map = self._build_local_var_map(child_table)

        if child_table is not None:
            self.current_table_stack.append(child_table)
            self.local_var_map_stack.append(local_map)
            self._invalidate_caches()

        if isinstance(node, ast.Lambda):
            self.visit(node.body)
        else:
            for stmt in node.body:
                self.visit(stmt)

        if child_table is not None:
            self.local_var_map_stack.pop()
            self.current_table_stack.pop()
            self._invalidate_caches()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_callable(node)

    def visit_Lambda(self, node):
        return self._visit_callable(node)

    def visit_Nonlocal(self, node):
        if not self._in_function_scope():
            return node

        new_names = []
        for name in node.names:
            mapped = self._resolve_renamed_name(name)
            new_names.append(mapped if mapped is not None else name)
        node.names = new_names
        return node

    def visit_ExceptHandler(self, node):
        if node.name and isinstance(node.name, str):
            mapped = self._resolve_renamed_name(node.name)
            if mapped is not None:
                node.name = mapped

        return self.generic_visit(node)

    def visit_Name(self, node):
        if not self._in_function_scope():
            return node

        mapped = self._resolve_renamed_name(node.id)
        if mapped is not None:
            node.id = mapped
        return node
