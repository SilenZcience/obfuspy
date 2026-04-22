"""
obfuscator
"""

import ast
import os
import symtable
from obfuspy.layers.obfBuiltins import ObfBuiltins
from obfuspy.util.charsets import CHARSETS
from obfuspy.util.randomizer import Randomizer
from obfuspy.util.randomizer import ALL_BUILTINS
from obfuspy.util.unparser import unparse
from obfuspy.layers.obfStringConstants import ObfStringConstants
from obfuspy.layers.obfNumericalConstants import ObfNumericalConstants
from obfuspy.layers.obfAntiTampering import ObfAntiTampering
from obfuspy.layers.obfDefArguments import ObfDefArguments
from obfuspy.layers.obfDefNames import ObfDefnames
from obfuspy.layers.obfClassVariables import ObfClassVariables
from obfuspy.layers.obfModuleVariables import ObfModuleVariables
from obfuspy.layers.obfClassNames import ObfClassNames


OBFUSCATE_NUMBERS = True
NUMERICAL_DENOMINATOR = 6
OBFUSCATE_STRINGS = True
OBFUSCATE_ASSIGNEMENTS = True
OBFUSCATE_ANNOTATIONS = True
OBFUSCATE_DOCSTRINGS = True

OBFUSCATE_VARIABLE_NAMES = False#
OBFUSCATE_ARGUMENT_NAMES = False#
OBFUSCATE_FUNCTION_NAMES = False#
OBFUSCATE_CLASS_NAMES = False#
VARIABLE_LENGTH = 5
VARIABLE_CHARSET = CHARSETS[0]

OBFUSCATE_IMPORTS = False#
OBFUSCATE_BUILTINS = False#

OBFUSCATE_ANTIDEBUG = False
ANTI_DEBUG_PROBABILITY = 0.2
OBFUSCATE_DEAD_CODE = False
DEAD_CODE_PROBABILITY = 1

OBFUSCATE_INDENTATION = False
INDENTATION_STRING = '\t\t\t'

OBFUSCATE_COMMENTS = False
COMMENT_LENGTH = 100
COMMENT_CHARSET = CHARSETS[0]


class Obfuscator:
    @staticmethod
    def _module_name_for(file_module, root_path: str) -> str:
        rel_path = os.path.relpath(file_module.in_path, root_path)
        rel_no_ext = os.path.splitext(rel_path)[0]
        parts = []
        for part in rel_no_ext.split(os.sep):
            if part == '__init__':
                continue
            parts.append(part)
        return '.'.join(parts)

    @staticmethod
    def _collect_project_exports(file_modules, randomizer: Randomizer, *, include_functions: bool, include_classes: bool) -> dict:
        export_map = {}

        def maybe_add_export(qualified_name: str, function_name: str) -> None:
            if function_name.startswith('__') and function_name.endswith('__'):
                return
            if function_name in ALL_BUILTINS:
                return
            if qualified_name not in export_map:
                export_map[qualified_name] = next(randomizer.random_name_gen)

        def walk(node, prefix_parts: list) -> None:
            if isinstance(node, ast.ClassDef):
                if include_classes:
                    qualified_name = '.'.join([*prefix_parts, node.name])
                    maybe_add_export(qualified_name, node.name)

                class_parts = [*prefix_parts, node.name]
                for child in node.body:
                    walk(child, class_parts)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if include_functions:
                    qualified_name = '.'.join([*prefix_parts, node.name])
                    maybe_add_export(qualified_name, node.name)

                callable_parts = [*prefix_parts, node.name]
                for child in node.body:
                    walk(child, callable_parts)
                return

            for field_name in ('body', 'orelse', 'finalbody'):
                child_body = getattr(node, field_name, None)
                if child_body:
                    for child in child_body:
                        walk(child, prefix_parts)
            for handler in getattr(node, 'handlers', []):
                for child in handler.body:
                    walk(child, prefix_parts)

        for file_module in file_modules:
            module_name = getattr(file_module, 'module_name', None)
            tree = getattr(file_module, 'tree', None)
            if not module_name or tree is None:
                continue

            for node in tree.body:
                walk(node, [module_name])

        return export_map


    @staticmethod
    def _collect_used_keyword_argument_names(file_modules) -> set:
        used = set()
        for file_module in file_modules:
            tree = getattr(file_module, 'tree', None)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        if keyword.arg is not None:
                            used.add(keyword.arg)
        return used

    @staticmethod
    def _collect_defined_names(file_modules) -> set:
        defined = set()

        class DefinedNameCollector(ast.NodeVisitor):
            @staticmethod
            def _add_arg_names(args_node) -> None:
                for arg in getattr(args_node, 'posonlyargs', []):
                    defined.add(arg.arg)
                for arg in getattr(args_node, 'args', []):
                    defined.add(arg.arg)
                for arg in getattr(args_node, 'kwonlyargs', []):
                    defined.add(arg.arg)
                vararg = getattr(args_node, 'vararg', None)
                if vararg is not None:
                    defined.add(vararg.arg)
                kwarg = getattr(args_node, 'kwarg', None)
                if kwarg is not None:
                    defined.add(kwarg.arg)

            @staticmethod
            def _add_target_names(target) -> None:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
                    return
                if isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        DefinedNameCollector._add_target_names(element)
                    return
                if isinstance(target, ast.Starred):
                    DefinedNameCollector._add_target_names(target.value)

            def visit_FunctionDef(self, node):
                defined.add(node.name)
                self._add_arg_names(node.args)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                defined.add(node.name)
                self._add_arg_names(node.args)
                self.generic_visit(node)

            def visit_Lambda(self, node):
                self._add_arg_names(node.args)
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                defined.add(node.name)
                self.generic_visit(node)

            def visit_Assign(self, node):
                for target in node.targets:
                    self._add_target_names(target)
                self.generic_visit(node)

            def visit_AnnAssign(self, node):
                self._add_target_names(node.target)
                self.generic_visit(node)

            def visit_AugAssign(self, node):
                self._add_target_names(node.target)
                self.generic_visit(node)

            def visit_For(self, node):
                self._add_target_names(node.target)
                self.generic_visit(node)

            def visit_AsyncFor(self, node):
                self._add_target_names(node.target)
                self.generic_visit(node)

            def visit_With(self, node):
                for item in node.items:
                    if item.optional_vars is not None:
                        self._add_target_names(item.optional_vars)
                self.generic_visit(node)

            def visit_AsyncWith(self, node):
                for item in node.items:
                    if item.optional_vars is not None:
                        self._add_target_names(item.optional_vars)
                self.generic_visit(node)

            def visit_ExceptHandler(self, node):
                if isinstance(node.name, str):
                    defined.add(node.name)
                self.generic_visit(node)

            def visit_Import(self, node):
                for name in node.names:
                    defined.add(name.asname or name.name.split('.')[0])
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                for name in node.names:
                    if name.name == '*':
                        continue
                    defined.add(name.asname or name.name)
                self.generic_visit(node)

            def visit_comprehension(self, node):
                self._add_target_names(node.target)
                self.generic_visit(node)

            def visit_NamedExpr(self, node):
                self._add_target_names(node.target)
                self.generic_visit(node)

        collector = DefinedNameCollector()
        for file_module in file_modules:
            tree = getattr(file_module, 'tree', None)
            if tree is None:
                continue
            collector.visit(tree)

        return defined

    @staticmethod
    def _collect_target_names(target) -> list:
        names = []
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                names.extend(Obfuscator._collect_target_names(element))
        return names

    @staticmethod
    def _collect_class_var_exports(file_modules, randomizer: Randomizer) -> dict:
        export_map = {}

        def collect_in_class_body(class_path: str, body: list) -> None:
            for stmt in body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    callable_parts = [*class_path.split('.'), stmt.name]
                    for child in stmt.body:
                        walk(child, callable_parts)
                    continue

                if isinstance(stmt, ast.ClassDef):
                    nested_path = f'{class_path}.{stmt.name}'
                    collect_in_class_body(nested_path, stmt.body)
                    continue

                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        for name in Obfuscator._collect_target_names(target):
                            export_map[f'{class_path}.{name}'] = next(randomizer.random_name_gen)
                elif isinstance(stmt, ast.AnnAssign):
                    for name in Obfuscator._collect_target_names(stmt.target):
                        export_map[f'{class_path}.{name}'] = next(randomizer.random_name_gen)
                elif isinstance(stmt, ast.AugAssign):
                    for name in Obfuscator._collect_target_names(stmt.target):
                        export_map[f'{class_path}.{name}'] = next(randomizer.random_name_gen)

                for field_name in ('body', 'orelse', 'finalbody'):
                    child_body = getattr(stmt, field_name, None)
                    if child_body:
                        collect_in_class_body(class_path, child_body)
                for handler in getattr(stmt, 'handlers', []):
                    collect_in_class_body(class_path, handler.body)

        def walk(node, prefix_parts: list) -> None:
            if isinstance(node, ast.ClassDef):
                class_parts = [*prefix_parts, node.name]
                collect_in_class_body('.'.join(class_parts), node.body)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                callable_parts = [*prefix_parts, node.name]
                for child in node.body:
                    walk(child, callable_parts)
                return

            for field_name in ('body', 'orelse', 'finalbody'):
                child_body = getattr(node, field_name, None)
                if child_body:
                    for child in child_body:
                        walk(child, prefix_parts)
            for handler in getattr(node, 'handlers', []):
                for child in handler.body:
                    walk(child, prefix_parts)

        for file_module in file_modules:
            module_name = getattr(file_module, 'module_name', None)
            tree = getattr(file_module, 'tree', None)
            if not module_name or tree is None:
                continue

            for node in tree.body:
                walk(node, [module_name])

        return export_map

    @staticmethod
    def _should_rename_module_var(name: str) -> bool:
        return not name.startswith('__') and name not in ALL_BUILTINS

    @staticmethod
    def _collect_module_targets(target) -> list:
        names = []
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                names.extend(Obfuscator._collect_module_targets(element))
        return names

    @staticmethod
    def _collect_module_var_exports_from_body(module_name: str, body: list, randomizer: Randomizer, export_map: dict) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    for name in Obfuscator._collect_module_targets(target):
                        if Obfuscator._should_rename_module_var(name):
                            export_map[f'{module_name}.{name}'] = next(randomizer.random_name_gen)
            elif isinstance(stmt, ast.AnnAssign):
                for name in Obfuscator._collect_module_targets(stmt.target):
                    if Obfuscator._should_rename_module_var(name):
                        export_map[f'{module_name}.{name}'] = next(randomizer.random_name_gen)
            elif isinstance(stmt, ast.AugAssign):
                for name in Obfuscator._collect_module_targets(stmt.target):
                    if Obfuscator._should_rename_module_var(name):
                        export_map[f'{module_name}.{name}'] = next(randomizer.random_name_gen)
            elif isinstance(stmt, ast.With):
                for item in stmt.items:
                    if item.optional_vars is not None:
                        for name in Obfuscator._collect_module_targets(item.optional_vars):
                            if Obfuscator._should_rename_module_var(name):
                                export_map[f'{module_name}.{name}'] = next(randomizer.random_name_gen)
            elif isinstance(stmt, ast.AsyncWith):
                for item in stmt.items:
                    if item.optional_vars is not None:
                        for name in Obfuscator._collect_module_targets(item.optional_vars):
                            if Obfuscator._should_rename_module_var(name):
                                export_map[f'{module_name}.{name}'] = next(randomizer.random_name_gen)

            for field_name in ('body', 'orelse', 'finalbody'):
                child_body = getattr(stmt, field_name, None)
                if child_body:
                    Obfuscator._collect_module_var_exports_from_body(module_name, child_body, randomizer, export_map)
            for handler in getattr(stmt, 'handlers', []):
                Obfuscator._collect_module_var_exports_from_body(module_name, handler.body, randomizer, export_map)

    @staticmethod
    def _collect_module_var_exports(file_modules, randomizer: Randomizer) -> dict:
        export_map = {}

        for file_module in file_modules:
            module_name = getattr(file_module, 'module_name', None)
            tree = getattr(file_module, 'tree', None)
            if not module_name or tree is None:
                continue

            Obfuscator._collect_module_var_exports_from_body(module_name, tree.body, randomizer, export_map)

        return export_map


    @staticmethod
    def _collect_argument_map_filtered(args_node, randomizer: Randomizer, keyword_blocklist: set) -> dict:
        arg_map = {}

        def maybe_add(arg_node):
            if arg_node is None:
                return
            if arg_node.arg in keyword_blocklist:
                return
            arg_map[arg_node.arg] = next(randomizer.random_name_gen)

        for arg in getattr(args_node, 'posonlyargs', []):
            maybe_add(arg)
        for arg in getattr(args_node, 'args', []):
            maybe_add(arg)
        for arg in getattr(args_node, 'kwonlyargs', []):
            maybe_add(arg)
        maybe_add(getattr(args_node, 'vararg', None))
        maybe_add(getattr(args_node, 'kwarg', None))

        return arg_map

    @staticmethod
    def _collect_argument_exports(file_modules, randomizer: Randomizer, function_exports: dict) -> dict:
        arg_export_map = {}
        keyword_blocklist = set(getattr(randomizer, 'project_context', {}).get('keyword_args_in_calls', set()))

        def walk(node, prefix_parts: list) -> None:
            if isinstance(node, ast.ClassDef):
                class_parts = [*prefix_parts, node.name]
                for child in node.body:
                    walk(child, class_parts)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                callable_parts = [*prefix_parts, node.name]
                qualified_name = '.'.join(callable_parts)
                arg_map = Obfuscator._collect_argument_map_filtered(node.args, randomizer, keyword_blocklist)
                arg_export_map[qualified_name] = arg_map

                exported_name = function_exports.get(qualified_name)
                if exported_name is not None:
                    arg_export_map['.'.join([*prefix_parts, exported_name])] = arg_map

                for child in node.body:
                    walk(child, callable_parts)
                return

            for field_name in ('body', 'orelse', 'finalbody'):
                child_body = getattr(node, field_name, None)
                if child_body:
                    for child in child_body:
                        walk(child, prefix_parts)
            for handler in getattr(node, 'handlers', []):
                for child in handler.body:
                    walk(child, prefix_parts)

        for file_module in file_modules:
            module_name = getattr(file_module, 'module_name', None)
            tree = getattr(file_module, 'tree', None)
            if not module_name or tree is None:
                continue

            for node in tree.body:
                walk(node, [module_name])

        return arg_export_map

    @staticmethod
    def obfuscate(settings: dict) -> None:
        randomizer = Randomizer()
        n = settings.get('random_name_length', 10)
        m = settings.get('random_comment_length', 10)
        charset_idx = settings.get('random_charset_index', 0)
        charset = CHARSETS[charset_idx] if 0 <= charset_idx < len(CHARSETS) else CHARSETS[0]
        randomizer.set_random_gen(n, m, charset)

        prefix   = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n'
        post_fix = '\n# Obfuscated by *obfuspy* (Silas A. Kraume)\n'

        file_modules = sorted(settings['file_modules'], key=lambda file_module: file_module.in_path)

        for file_module in file_modules:
            file_module.set_tree(ast.parse(file_module.in_code))
            file_module.set_symtable(symtable.symtable(file_module.in_code, file_module.in_path, 'exec'))

        if file_modules:
            common_root = os.path.commonpath([file_module.in_path for file_module in file_modules])
            if os.path.isfile(common_root):
                common_root = os.path.dirname(common_root)
        else:
            common_root = ''

        for file_module in file_modules:
            file_module.module_name = Obfuscator._module_name_for(file_module, common_root)

        randomizer.project_context = {
            'root_path': common_root,
            'module_names': {file_module.in_path: file_module.module_name for file_module in file_modules},
            'symbol_map': {},
            'keyword_args_in_calls': set(),
            'defined_names': Obfuscator._collect_defined_names(file_modules),
            'enabled_layers': {},
        }

        has_function_layer = any(layer is ObfDefnames for layer, _ in settings['obf_layers'])
        has_class_layer = any(layer is ObfClassNames for layer, _ in settings['obf_layers'])
        has_class_var_layer = any(layer is ObfClassVariables for layer, _ in settings['obf_layers'])
        has_module_var_layer = any(layer is ObfModuleVariables for layer, _ in settings['obf_layers'])
        has_argument_layer = any(layer is ObfDefArguments for layer, _ in settings['obf_layers'])

        randomizer.project_context['enabled_layers'] = {
            'functions': has_function_layer,
            'classes': has_class_layer,
            'class_vars': has_class_var_layer,
            'module_vars': has_module_var_layer,
            'arguments': has_argument_layer,
        }

        symbol_map = randomizer.project_context['symbol_map']
        function_export_map = {}

        if has_function_layer or has_class_layer:
            export_map = Obfuscator._collect_project_exports(
                file_modules,
                randomizer,
                include_functions=has_function_layer,
                include_classes=has_class_layer,
            )
            function_export_map = export_map
            for qualified_name, current_name in export_map.items():
                symbol_map[qualified_name] = {'name': current_name, 'kind': 'export'}

        if has_class_var_layer:
            class_var_map = Obfuscator._collect_class_var_exports(file_modules, randomizer)
            for qualified_name, current_name in class_var_map.items():
                symbol_map[qualified_name] = {'name': current_name, 'kind': 'class_var'}

        if has_module_var_layer:
            module_var_map = Obfuscator._collect_module_var_exports(file_modules, randomizer)
            for qualified_name, current_name in module_var_map.items():
                symbol_map[qualified_name] = {'name': current_name, 'kind': 'module_var'}

        if has_argument_layer:
            randomizer.project_context['keyword_args_in_calls'] = Obfuscator._collect_used_keyword_argument_names(file_modules)
            arg_exports = Obfuscator._collect_argument_exports(
                file_modules,
                randomizer,
                function_export_map,
            )
            for qualified_name, arg_map in arg_exports.items():
                for original_arg, current_arg in arg_map.items():
                    symbol_map[f'{qualified_name}::arg::{original_arg}'] = {'name': current_arg, 'kind': 'arg'}

        for layer, args in settings['obf_layers']:
            for file_module in file_modules:
                print(layer.__name__, file_module.in_path)
                l = layer(randomizer, file_module, *args)
                l.visit(file_module.tree)
                if any(isinstance(l, obfLayer) for obfLayer in (ObfStringConstants, ObfNumericalConstants, ObfBuiltins)):
                    ObfAntiTampering.HASH_NODES[file_module] = {k: v+[l] for k, v in ObfAntiTampering.HASH_NODES.get(file_module, {}).items()}


        for file_module in file_modules:
            out_code = unparse(file_module.tree, settings['indentation'])

            if settings['random_comment_length']:
                rnd_cmt_list = list(randomizer.generate_random_comments(out_code))
                file_module_lines = out_code.split('\n')
                for i, (_, rnd_cmt) in enumerate(zip(file_module_lines, rnd_cmt_list)):
                    file_module_lines[i] += f"#{rnd_cmt}"
                out_code = '\n'.join(file_module_lines)

            print('Finalizing file: ', file_module.in_path)
            out_code = prefix + out_code + post_fix
            out_code = ObfAntiTampering.finalize_hash_nodes(out_code, file_module)

            file_module.set_code(out_code)
