import ast

from obfuspy.util.domain import SYMBOL_MAP, Node


class ObfClassNames(ast.NodeTransformer):
    """
    Obfuscates class names.
    """

    def __init__(self, _, file_module) -> None:
        self.module_name = getattr(file_module, 'module_name', None)
        self.prefix_parts = []
        self._class_name_map_stack = []  # Stack of dicts: {original_name: obf_value}
        self._class_name_map_cache = {}

    def _push_class_name_scope(self):
        key = tuple((lbl.ltype, lbl.name) for lbl in self.prefix_parts)
        if key in self._class_name_map_cache:
            class_name_map = self._class_name_map_cache[key]
        else:
            class_name_map = SYMBOL_MAP.get_classes(self.prefix_parts)
            self._class_name_map_cache[key] = class_name_map
        self._class_name_map_stack.append(class_name_map)

    def _pop_class_name_scope(self):
        if self._class_name_map_stack:
            self._class_name_map_stack.pop()

    def _current_class_name_map(self):
        return self._class_name_map_stack[-1] if self._class_name_map_stack else {}

    # def _resolve_class_name_from_attr(self, attr_node):
    #     # Returns the obfuscated name for a class attribute chain, or None if not resolvable
    #     if not self.module_name:
    #         return None
    #     names = []
    #     node = attr_node
    #     while isinstance(node, ast.Attribute):
    #         names.append(node.attr)
    #         node = node.value
    #     if isinstance(node, ast.Name):
    #         names.append(node.id)
    #     else:
    #         return None
    #     names = list(reversed(names))
    #     # Only support top-level (module) classes for now
    #     for i in range(len(names), 0, -1):
    #         class_path = names[:i]
    #         label_path = [Node.Module(self.module_name)]
    #         for cname in class_path:
    #             label_path.append(Node.Cls(cname))
    #         class_map = SYMBOL_MAP.get_classes(label_path) # needs cache if ever used
    #         if names[-1] in class_map:
    #             return class_map[names[-1]]
    #     return None

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self._class_name_map_stack = []
        self._push_class_name_scope()
        self.generic_visit(node)
        self._pop_class_name_scope()
        return node

    def visit_ClassDef(self, node):
        class_name_map = self._current_class_name_map()
        original_name = node.name
        self.prefix_parts.append(Node.Cls(node.name))
        self._push_class_name_scope()
        renamed = False
        if node.name in class_name_map:
            obf_name = class_name_map[node.name]['name']
            node.name = obf_name
            renamed = True
        self.generic_visit(node)
        self._pop_class_name_scope()
        self.prefix_parts.pop()
        if renamed:
            return [node, self._alias_assign(original_name, obf_name, node)]
        return node

    def visit_FunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        self._push_class_name_scope()
        self.generic_visit(node)
        self._pop_class_name_scope()
        self.prefix_parts.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        self._push_class_name_scope()
        self.generic_visit(node)
        self._pop_class_name_scope()
        self.prefix_parts.pop()
        return node

    def visit_Name(self, node):
        # Only obfuscate class name loads if in current class name map
        if self._class_name_map_stack and isinstance(node.ctx, ast.Load):
            class_name_map = self._current_class_name_map()
            if node.id in class_name_map:
                node.id = class_name_map[node.id]['name']
        return node

    # def visit_Attribute(self, node): # TODO: Class.classvar should obfusacte "Class"
    #     obf_name = self._resolve_class_name_from_attr(node)
    #     if obf_name:
    #         node.attr = obf_name
    #     self.generic_visit(node)
    #     return node
