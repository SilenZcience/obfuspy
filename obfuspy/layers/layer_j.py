import ast

from obfuspy.util.randomizer import Randomizer


class Layer_J(ast.NodeTransformer):
    """
    Layer J obfuscates function/method arguments using precomputed maps from
    the obfuscator project context.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)
        self.arg_stack = [{}]
        self.class_stack = []
        self.callable_stack = []

    def _arg_map_for_qualified(self, qualified_name: str):
        return self.project_context.get('arg_exports', {}).get(qualified_name)

    def _current_callable_qualified_name(self, node):
        parts = [self.module_name] if self.module_name else []
        if self.class_stack:
            parts.extend(self.class_stack)
        if self.callable_stack:
            parts.extend(self.callable_stack)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parts.append(node.name)
        return '.'.join(part for part in parts if part)

    def _rename_arguments(self, args) -> dict:
        arg_map = {}
        for arg in args:
            if arg is None:
                continue
            arg_map[arg.arg] = next(self.randomizer.random_name_gen)
            arg.arg = arg_map[arg.arg]
        return arg_map

    def _rename_arguments_from_map(self, args, arg_map: dict) -> dict:
        renamed_map = {}
        for arg in args:
            if arg is None:
                continue
            mapped_name = arg_map.get(arg.arg)
            if mapped_name is not None:
                renamed_map[arg.arg] = mapped_name
                arg.arg = mapped_name
        return renamed_map

    def _visit_callable(self, node):
        qualified_name = self._current_callable_qualified_name(node)
        exported_arg_map = None if isinstance(node, ast.Lambda) else self._arg_map_for_qualified(qualified_name)

        arg_map = {}
        if exported_arg_map is None:
            arg_map.update(self._rename_arguments(getattr(node.args, 'posonlyargs', [])))
            arg_map.update(self._rename_arguments(node.args.args))
            arg_map.update(self._rename_arguments(node.args.kwonlyargs))
            arg_map.update(self._rename_arguments([node.args.vararg]))
            arg_map.update(self._rename_arguments([node.args.kwarg]))
        else:
            arg_map.update(self._rename_arguments_from_map(getattr(node.args, 'posonlyargs', []), exported_arg_map))
            arg_map.update(self._rename_arguments_from_map(node.args.args, exported_arg_map))
            arg_map.update(self._rename_arguments_from_map(node.args.kwonlyargs, exported_arg_map))
            arg_map.update(self._rename_arguments_from_map([node.args.vararg], exported_arg_map))
            arg_map.update(self._rename_arguments_from_map([node.args.kwarg], exported_arg_map))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.callable_stack.append(node.name)

        self.arg_stack.append(arg_map)
        self.generic_visit(node)
        self.arg_stack.pop()

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.callable_stack.pop()

        return node

    def visit_Module(self, node):
        self.arg_stack = [{}]
        self.class_stack = []
        self.callable_stack = []
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
