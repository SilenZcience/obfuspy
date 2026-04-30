import ast

from obfuspy.util.domain import SYMBOL_MAP, Node


class ObfDefnames(ast.NodeTransformer):
    """
    Obfuscates function names and all function calls with obfuscated names using symbol map.
    """
    FIRST_PASS = True

    def __init__(self, _, file_module) -> None:
        self.module_name = getattr(file_module, 'module_name', None)
        self.prefix_parts = []
        self._def_name_map_stack = []  # Stack of dicts: {original_name: obf_value}
        self._def_name_map_cache = {}

    def _push_def_name_scope(self):
        key = tuple((lbl.ltype, lbl.name) for lbl in self.prefix_parts)
        if key in self._def_name_map_cache:
            def_map = self._def_name_map_cache[key]
        else:
            def_map = SYMBOL_MAP.get_functions(self.prefix_parts)
            self._def_name_map_cache[key] = def_map
        self._def_name_map_stack.append(def_map)

    def _pop_def_name_scope(self):
        if self._def_name_map_stack:
            self._def_name_map_stack.pop()

    def _current_def_name_map(self):
        return self._def_name_map_stack[-1] if self._def_name_map_stack else {}

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign: # TODO: insert at random position before fist usage
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self._def_name_map_stack = []
        self._push_def_name_scope()
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.prefix_parts.append(Node.Cls(node.name))
        self._push_def_name_scope()
        self.generic_visit(node)
        self._pop_def_name_scope()
        self.prefix_parts.pop()
        return node

    def visit_FunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        def_map = self._current_def_name_map()
        renamed = False
        original_name = node.name
        if node.name in def_map:
            obf_name = def_map[node.name]['name']
            node.name = obf_name
            renamed = True
        self._push_def_name_scope()
        self.generic_visit(node)
        self._pop_def_name_scope()
        self.prefix_parts.pop()
        if renamed:
            return [node, self._alias_assign(original_name, obf_name, node)]
        return node

    def visit_AsyncFunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        def_map = self._current_def_name_map()
        renamed = False
        original_name = node.name
        if node.name in def_map:
            obf_name = def_map[node.name]['name']
            node.name = obf_name
            renamed = True
        self._push_def_name_scope()
        self.generic_visit(node)
        self._pop_def_name_scope()
        self.prefix_parts.pop()
        if renamed:
            return [node, self._alias_assign(original_name, obf_name, node)]
        return node

    def visit_Name(self, node):
        # Only obfuscate function name loads if in current def map
        if ObfDefnames.FIRST_PASS and self._def_name_map_stack and isinstance(node.ctx, ast.Load):
            def_map = self._current_def_name_map()
            if node.id in def_map:
                node.id = def_map[node.id]['name']
        return node

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            def_map = self._current_def_name_map()
            if node.func.id in def_map:
                node.func.id = def_map[node.func.id]['name']
        self.generic_visit(node)
        return node
