import ast
from obfuspy.util.randomizer import Randomizer, BUILTINS_DEFAULT


class ObfClassNames(ast.NodeTransformer):
    """
    Obfuscates class names.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)
        self.scope_name_stack = []
        self.module_class_map = {}

    def _export_name(self, qualified_name: str):
        entry = self.project_context.get('symbol_map', {}).get(qualified_name)
        if isinstance(entry, dict):
            return entry.get('name')
        return entry

    def _set_export_name(self, qualified_name: str, obfuscated_name: str) -> None:
        symbol_map = self.project_context.setdefault('symbol_map', {})
        symbol_map[qualified_name] = {'name': obfuscated_name, 'kind': 'export'}

    def _qualified_class_name(self, class_name: str) -> str:
        return '.'.join([self.module_name] + self.scope_name_stack + [class_name])

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def visit_ClassDef(self, node):
        original_name = node.name
        renamed = False

        if self.module_name is not None:
            qualified_name = self._qualified_class_name(original_name)
            export_name = self._export_name(qualified_name)
            if export_name is not None:
                node.name = export_name
                self._set_export_name(qualified_name, export_name)
                renamed = True
                if not self.scope_name_stack:
                    self.module_class_map[original_name] = export_name

        self.scope_name_stack.append(original_name)
        self.generic_visit(node)
        self.scope_name_stack.pop()

        if renamed:
            return [node, self._alias_assign(original_name, node.name, node)]
        return node

    def visit_FunctionDef(self, node):
        self.scope_name_stack.append(node.name)
        self.generic_visit(node)
        self.scope_name_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.scope_name_stack.append(node.name)
        self.generic_visit(node)
        self.scope_name_stack.pop()
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.module_class_map:
            node.id = self.module_class_map[node.id]
        return node
