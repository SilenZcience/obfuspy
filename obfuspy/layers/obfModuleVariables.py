import ast

from obfuspy.util.domain import SYMBOL_MAP, Node


class ObfModuleVariables(ast.NodeTransformer):
    """
    Obfuscates module-level variables.
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

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self._symtable_map_scope = [self.file_module.symtable]
        self.module_vars = SYMBOL_MAP.get_modulevars(self.prefix_parts)
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
        aliases = []
        if len(self._symtable_map_scope) == 1:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    obf_name = self._resolve_module_var_name(target.id)
                    if obf_name != target.id:
                        aliases.append(self._alias_assign(target.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_AnnAssign(self, node):
        aliases = []
        if isinstance(node.target, ast.Name) and len(self._symtable_map_scope) == 1:
            obf_name = self._resolve_module_var_name(node.target.id)
            if obf_name != node.target.id:
                aliases.append(self._alias_assign(node.target.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_AugAssign(self, node):
        aliases = []
        if isinstance(node.target, ast.Name) and len(self._symtable_map_scope) == 1:
            obf_name = self._resolve_module_var_name(node.target.id)
            if obf_name != node.target.id:
                aliases.append(self._alias_assign(node.target.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_For(self, node):
        aliases = []
        if len(self._symtable_map_scope) == 1:
            if isinstance(node.target, ast.Name):
                obf_name = self._resolve_module_var_name(node.target.id)
                if obf_name != node.target.id:
                    aliases.append(self._alias_assign(node.target.id, obf_name, node))
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for element in node.target.elts:
                    if isinstance(element, ast.Name):
                        obf_name = self._resolve_module_var_name(element.id)
                        if obf_name != element.id:
                            aliases.append(self._alias_assign(element.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_AsyncFor(self, node):
        aliases = []
        if len(self._symtable_map_scope) == 1:
            if isinstance(node.target, ast.Name):
                obf_name = self._resolve_module_var_name(node.target.id)
                if obf_name != node.target.id:
                    aliases.append(self._alias_assign(node.target.id, obf_name, node))
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for element in node.target.elts:
                    if isinstance(element, ast.Name):
                        obf_name = self._resolve_module_var_name(element.id)
                        if obf_name != element.id:
                            aliases.append(self._alias_assign(element.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_With(self, node):
        aliases = []
        if len(self._symtable_map_scope) == 1:
            for item in node.items:
                if item.optional_vars is None:
                    continue
                if isinstance(item.optional_vars, ast.Name):
                    obf_name = self._resolve_module_var_name(item.optional_vars.id)
                    if obf_name != item.optional_vars.id:
                        aliases.append(self._alias_assign(item.optional_vars.id, obf_name, node))
                elif isinstance(item.optional_vars, (ast.Tuple, ast.List)):
                    for element in item.optional_vars.elts:
                        if isinstance(element, ast.Name):
                            obf_name = self._resolve_module_var_name(element.id)
                            if obf_name != element.id:
                                aliases.append(self._alias_assign(element.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_AsyncWith(self, node):
        aliases = []
        if len(self._symtable_map_scope) == 1:
            for item in node.items:
                if item.optional_vars is None:
                    continue
                if isinstance(item.optional_vars, ast.Name):
                    obf_name = self._resolve_module_var_name(item.optional_vars.id)
                    if obf_name != item.optional_vars.id:
                        aliases.append(self._alias_assign(item.optional_vars.id, obf_name, node))
                elif isinstance(item.optional_vars, (ast.Tuple, ast.List)):
                    for element in item.optional_vars.elts:
                        if isinstance(element, ast.Name):
                            obf_name = self._resolve_module_var_name(element.id)
                            if obf_name != element.id:
                                aliases.append(self._alias_assign(element.id, obf_name, node))
        self.generic_visit(node)
        return [node, *aliases] if aliases else node

    def visit_Global(self, node):
        expanded_names = []
        for name in node.names:
            obfuscated_name = self._resolve_module_var_name(name)
            expanded_names.append(obfuscated_name)
        node.names = list(dict.fromkeys(expanded_names))
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.name and isinstance(node.name, str):
            node.name = self._resolve_module_var_name(node.name)
        return self.generic_visit(node)

    def _resolve_module_var_name(self, node_name: str):
        current_symtable = self._current_symtable_map()
        global_symbol = self.module_vars.get(node_name)
        if global_symbol is None:
            return node_name
        original_name = global_symbol['original']
        try:
            current_symbol = current_symtable.lookup(node_name)
        except KeyError:
            current_symbol = None
        if current_symbol is None:
            try:
                current_symbol = current_symtable.lookup(original_name)
            except KeyError:
                return node_name
        if current_symbol.is_parameter() or current_symbol.is_imported():
            return node_name
        if not current_symbol.is_global() or (current_symbol.is_local() and len(self._symtable_map_scope) > 1):
            return node_name
        return global_symbol['name']

    def visit_Name(self, node):
        node.id = self._resolve_module_var_name(node.id)
        return node
