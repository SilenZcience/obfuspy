import ast

from obfuspy.util.domain import SYMBOL_MAP, Node


class ObfGlobals(ast.NodeTransformer):
    """
    Obfuscates module-level variables to be accessed via globals().
    """

    def __init__(self, _, file_module) -> None:
        self.file_module = file_module
        self.symtable = file_module.symtable
        self.module_name = getattr(file_module, 'module_name', None)
        self.module_vars = None
        self.prefix_parts = []
        self._symtable_map_scope = []

    def _push_symtable_scope(self, node, original_name: str):
        current_table = self._current_symtable_map()
        if current_table is None:
            return
        candidates = []
        for child in current_table.get_children():
            if child.get_name() == original_name and child.get_lineno() == getattr(node, 'lineno', None):
                candidates.append(child)
        if candidates:
            self._symtable_map_scope.append(candidates[0])
            return
        for child in current_table.get_children():
            if child.get_name() == node.name:
                self._symtable_map_scope.append(child)
                return

    def _pop_symtable_scope(self):
        if self._symtable_map_scope:
            self._symtable_map_scope.pop()

    def _current_symtable_map(self):
        return self._symtable_map_scope[-1] if self._symtable_map_scope else None

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self._symtable_map_scope = [self.file_module.symtable]
        self.module_vars = SYMBOL_MAP.get_modulevars(self.prefix_parts, get_all=True)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.prefix_parts.append(Node.Cls(node.name))
        obf_value = SYMBOL_MAP.get(self.prefix_parts)
        if obf_value:
            original_name = obf_value['original']
            self._push_symtable_scope(node, original_name)
        self.generic_visit(node)
        if obf_value:
            self._pop_symtable_scope()
        self.prefix_parts.pop()
        return node

    def visit_FunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        obf_value = SYMBOL_MAP.get(self.prefix_parts)
        if obf_value:
            original_name = obf_value['original']
            self._push_symtable_scope(node, original_name)
        self.generic_visit(node)
        if obf_value:
            self._pop_symtable_scope()
        self.prefix_parts.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        obf_value = SYMBOL_MAP.get(self.prefix_parts)
        if obf_value:
            original_name = obf_value['original']
            self._push_symtable_scope(node, original_name)
        self.generic_visit(node)
        if obf_value:
            self._pop_symtable_scope()
        self.prefix_parts.pop()
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)

        new_nodes = []

        for target in node.targets:
            if isinstance(target, ast.Name):
                if self._is_module_var(target.id):
                    new_nodes.append(self._globals_set(target.id, node.value, node))
                    continue

            fallback_node = ast.Assign(targets=[target], value=node.value)
            new_nodes.append(ast.copy_location(fallback_node, node))

        return new_nodes if len(new_nodes) > 1 else new_nodes[0]

    def visit_AnnAssign(self, node):
        self.generic_visit(node)

        if isinstance(node.target, ast.Name) and self._is_module_var(node.target.id):
            return self._globals_set(node.target.id, node.value, node)

        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)

        if isinstance(node.target, ast.Name) and self._is_module_var(node.target.id):
            new_value = ast.BinOp(
                left=self._globals_get(node.target.id, node),
                op=node.op,
                right=node.value,
            )
            return self._globals_set(node.target.id, new_value, node)

        return node

    def visit_Delete(self, node):
        new_targets = []
        fallback_targets = []
        for target in node.targets:
            if isinstance(target, ast.Name) and self._is_module_var(target.id):
                new_targets.append(self._globals_del(target.id, node))
            else:
                fallback_targets.append(target)
        if fallback_targets:
            new_targets.append(ast.Delete(targets=fallback_targets))
        return new_targets

    def _is_module_var(self, node_name: str):
        current_symtable = self._current_symtable_map()
        global_symbol = self.module_vars.get(node_name)
        if global_symbol is None:
            return False
        original_name = global_symbol['original']
        try:
            current_symbol = current_symtable.lookup(node_name)
        except KeyError:
            current_symbol = None
        if current_symbol is None:
            try:
                current_symbol = current_symtable.lookup(original_name)
            except KeyError:
                return False
        if current_symbol.is_parameter() or current_symbol.is_imported():
            return False
        if not current_symbol.is_global() or (current_symbol.is_local() and len(self._symtable_map_scope) > 1):
            return False
        return True

    def _globals_call(self, source_node):
        node = ast.Call(
            func=ast.Name(id="globals", ctx=ast.Load()),
            args=[],
            keywords=[]
        )
        return ast.copy_location(node, source_node)

    def _globals_get(self, name: str, source_node):
        node = ast.Subscript(
            value=self._globals_call(source_node),
            slice=ast.Constant(value=name),
            ctx=ast.Load(),
        )

        node = ast.copy_location(node, source_node)
        return node

    def _globals_set(self, name: str, value, source_node):
        node = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=self._globals_call(source_node),
                    attr="__setitem__",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=name), value],
                keywords=[],
            )
        )

        node = ast.copy_location(node, source_node)
        return node

    def _globals_del(self, name: str, source_node):
        node = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=self._globals_call(source_node),
                    attr="__delitem__",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=name)],
                keywords=[],
            )
        )

        node = ast.copy_location(node, source_node)
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and self._is_module_var(node.id):
            return self._globals_get(node.id, node)

        return node
