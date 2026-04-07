import ast
from obfuspy.util.randomizer import Randomizer, BUILTINS_DEFAULT


class Layer_K(ast.NodeTransformer):
    """
    Layer K obfuscates function names in the AST, ensuring that functions
    pointing to external objects (e.g., imported modules or attributes) are not obfuscated.
    """
    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)
        self.module_function_map = {}
        self.scope_name_stack = []
        self.class_context_stack = []

    def _export_name(self, qualified_name: str):
        return self.project_context.get('exports', {}).get(qualified_name)

    def _qualified_callable_name(self, function_name: str) -> str:
        return '.'.join([self.module_name] + self.scope_name_stack + [function_name])

    def _should_rename(self, name: str) -> bool:
        return not (name.startswith('__') and name.endswith('__')) and name not in BUILTINS_DEFAULT

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        alias_node = ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )
        return alias_node

    def visit_ClassDef(self, node):
        self.scope_name_stack.append(node.name)

        method_map = {}
        method_reverse_map = {}
        new_body = []

        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and self._should_rename(child.name):
                original_name = child.name
                qualified_name = self._qualified_callable_name(child.name)
                export_name = self._export_name(qualified_name)
                if export_name is not None:
                    method_map[original_name] = export_name
                    method_reverse_map[export_name] = original_name
                    child.name = export_name
                    new_body.append(child)
                    new_body.append(self._alias_assign(original_name, export_name, child))
                    continue
            new_body.append(child)
        node.body = new_body

        self.class_context_stack.append({
            'name': node.name,
            'method_map': method_map,
            'method_reverse_map': method_reverse_map,
        })
        self.generic_visit(node)
        self.class_context_stack.pop()
        self.scope_name_stack.pop()
        return node

    def _visit_callable(self, node):
        class_ctx = self.class_context_stack[-1] if self.class_context_stack else None

        # Direct class method: name was already obfuscated in visit_ClassDef.
        if (
            class_ctx is not None and
            self.scope_name_stack and
            self.scope_name_stack[-1] == class_ctx['name'] and
            node.name in class_ctx['method_reverse_map']
        ):
            # Direct class method: name is already obfuscated in visit_ClassDef.
            original_name = class_ctx['method_reverse_map'][node.name]
            self.scope_name_stack.append(original_name)
            self.generic_visit(node)
            self.scope_name_stack.pop()
            return node

        if self.module_name is not None and self._should_rename(node.name):
            original_name = node.name
            qualified_name = self._qualified_callable_name(original_name)
            export_name = self._export_name(qualified_name)
            if export_name is not None:
                self.module_function_map[original_name] = export_name
                node.name = export_name
                self.scope_name_stack.append(original_name)
                self.generic_visit(node)
                self.scope_name_stack.pop()
                return [node, self._alias_assign(original_name, export_name, node)]

        self.scope_name_stack.append(node.name)
        self.generic_visit(node)
        self.scope_name_stack.pop()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_callable(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.module_function_map:
            node.id = self.module_function_map[node.id]
        return node

    def visit_Attribute(self, node):
        class_ctx = self.class_context_stack[-1] if self.class_context_stack else None
        if class_ctx is not None and isinstance(node.value, ast.Name):
            current_class_name = class_ctx['name']
            current_method_map = class_ctx['method_map']
            if node.value.id in {"self", "cls", current_class_name} and node.attr in current_method_map:
                node.attr = current_method_map[node.attr]
        self.generic_visit(node)
        return node
