import ast


class ObfDefArguments(ast.NodeTransformer):
    """
    Obfuscates function/method arguments using the export map.
    Only arguments present in the export map are renamed.
    """
    def __init__(self, randomizer, file_module):
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)
        self.arg_stack = [{}]
        self.class_stack = []
        self.function_stack = []

    def _arg_map_for_qualified(self, qualified_name):
        symbol_map = self.project_context.get('symbol_map', {})
        if not isinstance(symbol_map, dict):
            return {}
        prefix = f'{qualified_name}::arg::'
        arg_map = {}
        for key, value in symbol_map.items():
            if not key.startswith(prefix):
                continue
            if isinstance(value, dict) and value.get('kind') != 'arg':
                continue
            original_arg = key[len(prefix):]
            arg_map[original_arg] = value.get('name') if isinstance(value, dict) else value
        return arg_map

    def _current_callable_qualified_name(self, node):
        parts = [self.module_name] if self.module_name else []
        if self.class_stack:
            parts.extend(self.class_stack)
        if self.function_stack:
            parts.extend(self.function_stack)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parts.append(node.name)
        return '.'.join(part for part in parts if part)

    def _visit_callable(self, node):
        qualified_name = self._current_callable_qualified_name(node)
        arg_map = self._arg_map_for_qualified(qualified_name)
        # Rename only arguments present in the export map
        for arg in getattr(node.args, 'posonlyargs', []):
            if arg and arg.arg in arg_map:
                arg.arg = arg_map[arg.arg]
        for arg in getattr(node.args, 'args', []):
            if arg and arg.arg in arg_map:
                arg.arg = arg_map[arg.arg]
        for arg in getattr(node.args, 'kwonlyargs', []):
            if arg and arg.arg in arg_map:
                arg.arg = arg_map[arg.arg]
        if getattr(node.args, 'vararg', None) and node.args.vararg.arg in arg_map:
            node.args.vararg.arg = arg_map[node.args.vararg.arg]
        if getattr(node.args, 'kwarg', None) and node.args.kwarg.arg in arg_map:
            node.args.kwarg.arg = arg_map[node.args.kwarg.arg]
        self.arg_stack.append(arg_map)
        # Push function name for nested functions before visiting children
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.function_stack.append(node.name)

        if isinstance(node, ast.Lambda):
            self.visit(node.body)
        else:
            for stmt in node.body:
                self.visit(stmt)
        # Pop function name
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.function_stack.pop()
        self.arg_stack.pop()
        return node

    def visit_Module(self, node):
        self.arg_stack = [{}]
        self.class_stack = []
        self.function_stack = []
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_callable(node)

    def visit_Lambda(self, node):
        return self._visit_callable(node)

    def visit_Name(self, node):
        for scope in reversed(self.arg_stack):
            if node.id in scope:
                node.id = scope[node.id]
                break
        return node
