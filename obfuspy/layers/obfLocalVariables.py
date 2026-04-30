import ast

from obfuspy.util.domain import SYMBOL_MAP, Node
from obfuspy.util.randomizer import Randomizer


class ObfLocalVariables(ast.NodeTransformer):
    """
    Obfuscates local variables.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.module_name = getattr(file_module, 'module_name', None)
        self.prefix_parts = []
        self._symtable_map_scope = []
        self._localvar_name_map_stack = []

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

    def _push_localvar_scope(self):
        current_symtable = self._current_symtable_map()
        if current_symtable is None or current_symtable.get_type() != 'function':
            self._localvar_name_map_stack.append({})
            return

        localvar_name_map = {}
        for symbol in current_symtable.get_symbols():
            if symbol.is_parameter() or symbol.is_imported():
                continue
            if not symbol.is_local():
                continue
            if hasattr(symbol, 'is_namespace') and symbol.is_namespace():
                continue
            localvar_name_map[symbol.get_name()] = next(self.randomizer.random_name_gen)
        self._localvar_name_map_stack.append(localvar_name_map)

    def _pop_localvar_scope(self):
        if self._localvar_name_map_stack:
            self._localvar_name_map_stack.pop()

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self._symtable_map_scope = [self.file_module.symtable]
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

    def _visit_callable(self, node):
        self.prefix_parts.append(Node.Def(node.name))

        for deco in node.decorator_list:
            self.visit(deco)
        self.visit(node.args)
        if node.returns:
            self.visit(node.returns)

        obf_value = SYMBOL_MAP.get(self.prefix_parts)
        if obf_value:
            original_name = obf_value['original']
            self._push_symtable_scope(node, original_name)
            self._push_localvar_scope()

        for stmt in node.body:
            self.visit(stmt)

        if obf_value:
            self._pop_localvar_scope()
            self._pop_symtable_scope()
        self.prefix_parts.pop()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_callable(node)

    def visit_Nonlocal(self, node):
        new_names = []
        for name in node.names:
            new_names.append(self._resolve_local_var_name(name))
        node.names = new_names
        return node

    def visit_ExceptHandler(self, node):
        if node.name and isinstance(node.name, str):
            node.name = self._resolve_local_var_name(node.name)
        return self.generic_visit(node)

    def _resolve_local_var_name(self, node_name: str):
        for scope in reversed(self._localvar_name_map_stack):
            if node_name not in scope:
                continue
            return scope[node_name]
        return node_name

    def visit_Name(self, node):
        node.id = self._resolve_local_var_name(node.id)
        return node
