import ast

from obfuspy.util.randomizer import Randomizer


class Layer_N(ast.NodeTransformer):
    """
    Layer N obfuscates local variables in function scopes (including nested ones).

    This layer does not obfuscate module variables, class variables, function names,
    class names, imports, or argument names.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.current_table_stack = []
        self.local_var_map_stack = []

    def _lookup_symbol(self, table, name: str):
        if table is None:
            return None
        try:
            return table.lookup(name)
        except KeyError:
            return None

    def _child_table_for(self, node):
        current_table = self.current_table_stack[-1] if self.current_table_stack else None
        if current_table is None:
            return None

        node_name = 'lambda' if isinstance(node, ast.Lambda) else getattr(node, 'name', None)
        node_lineno = getattr(node, 'lineno', None)

        expected_type = 'class' if isinstance(node, ast.ClassDef) else 'function'
        typed_children = [child for child in current_table.get_children() if child.get_type() == expected_type]

        # Prefer line-based matching so this still works if another layer renamed
        # function/class names before this layer runs.
        if node_lineno is not None:
            line_matches = [child for child in typed_children if child.get_lineno() == node_lineno]
            if len(line_matches) == 1:
                return line_matches[0]
            if line_matches and node_name is not None:
                for child in line_matches:
                    if child.get_name() == node_name:
                        return child
                return line_matches[0]

        if node_name is not None:
            for child in typed_children:
                if child.get_name() == node_name:
                    return child

        if typed_children:
            return typed_children[0]
        return None

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
        # Resolve lexical names from inner to outer scope.
        for idx in range(len(self.current_table_stack) - 1, -1, -1):
            table = self.current_table_stack[idx]
            symbol = self._lookup_symbol(table, name)
            if symbol is None:
                continue

            if symbol.is_global() or symbol.is_imported() or symbol.is_parameter():
                return None

            if symbol.is_local():
                return self.local_var_map_stack[idx].get(name)

            if symbol.is_free() or symbol.is_nonlocal():
                continue

            return None

        return None

    def visit_Module(self, node):
        self.current_table_stack = [self.file_module.symtable]
        self.local_var_map_stack = [{}]
        self.generic_visit(node)
        self.local_var_map_stack.pop()
        self.current_table_stack.pop()
        return node

    def visit_ClassDef(self, node):
        child_table = self._child_table_for(node)
        if child_table is not None:
            self.current_table_stack.append(child_table)
            self.local_var_map_stack.append({})

        self.generic_visit(node)

        if child_table is not None:
            self.local_var_map_stack.pop()
            self.current_table_stack.pop()
        return node

    def _visit_callable(self, node):
        child_table = self._child_table_for(node)
        local_map = self._build_local_var_map(child_table)

        if child_table is not None:
            self.current_table_stack.append(child_table)
            self.local_var_map_stack.append(local_map)

        self.generic_visit(node)

        if child_table is not None:
            self.local_var_map_stack.pop()
            self.current_table_stack.pop()
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

    def visit_Name(self, node):
        if not self._in_function_scope():
            return node

        mapped = self._resolve_renamed_name(node.id)
        if mapped is not None:
            node.id = mapped
        return node
