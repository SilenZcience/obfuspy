import ast

from obfuspy.util.randomizer import Randomizer


class ObfDefArguments(ast.NodeTransformer):
    """
    Obfuscates function/method arguments.
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
        symbol_map = self.project_context.get('symbol_map', {})
        if not isinstance(symbol_map, dict):
            return None

        prefix = f'{qualified_name}::arg::'
        arg_map = {}
        for key, value in symbol_map.items():
            if not key.startswith(prefix):
                continue
            if isinstance(value, dict) and value.get('kind') != 'arg':
                continue
            original_arg = key[len(prefix):]
            arg_map[original_arg] = value.get('name') if isinstance(value, dict) else value
        return arg_map or None

    def _current_arg_exports_dict(self) -> dict:
        symbol_map = self.project_context.setdefault('symbol_map', {})
        if isinstance(symbol_map, dict):
            return symbol_map
        return {}

    def _set_current_arg_map(self, qualified_name: str, arg_map: dict) -> None:
        if not qualified_name:
            return
        exports = self._current_arg_exports_dict()
        for original_arg, current_arg in arg_map.items():
            exports[f'{qualified_name}::arg::{original_arg}'] = {'name': current_arg, 'kind': 'arg'}

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

        if not isinstance(node, ast.Lambda):
            self._set_current_arg_map(qualified_name, arg_map)

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
