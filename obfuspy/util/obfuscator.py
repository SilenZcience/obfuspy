"""
obfuscator
"""

import ast
import os
import symtable
from obfuspy.util.charsets import CHARSETS
from obfuspy.util.randomizer import Randomizer
from obfuspy.util.randomizer import ALL_BUILTINS
from obfuspy.util.unparser import unparse
from obfuspy.layers.layer_j import Layer_J
from obfuspy.layers.layer_k import Layer_K
from obfuspy.layers.layer_l import Layer_L
from obfuspy.layers.layer_m import Layer_M


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
    def _collect_project_exports(file_modules, randomizer: Randomizer) -> dict:
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
                class_parts = [*prefix_parts, node.name]
                for child in node.body:
                    walk(child, class_parts)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
    def _reverse_export_map(export_map: dict) -> dict:
        return {obfuscated_name: qualified_name for qualified_name, obfuscated_name in export_map.items()}

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
    def _should_rename_class_var(name: str) -> bool:
        return not name.startswith('__')

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
    def _collect_class_var_exports_from_body(class_path: str, body: list, randomizer: Randomizer, export_map: dict) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(stmt, ast.ClassDef):
                nested_path = f'{class_path}.{stmt.name}'
                Obfuscator._collect_class_var_exports_from_body(nested_path, stmt.body, randomizer, export_map)
                continue

            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    for name in Obfuscator._collect_target_names(target):
                        if Obfuscator._should_rename_class_var(name):
                            export_map[f'{class_path}.{name}'] = next(randomizer.random_name_gen)
            elif isinstance(stmt, ast.AnnAssign):
                for name in Obfuscator._collect_target_names(stmt.target):
                    if Obfuscator._should_rename_class_var(name):
                        export_map[f'{class_path}.{name}'] = next(randomizer.random_name_gen)
            elif isinstance(stmt, ast.AugAssign):
                for name in Obfuscator._collect_target_names(stmt.target):
                    if Obfuscator._should_rename_class_var(name):
                        export_map[f'{class_path}.{name}'] = next(randomizer.random_name_gen)

            for field_name in ('body', 'orelse', 'finalbody'):
                child_body = getattr(stmt, field_name, None)
                if child_body:
                    Obfuscator._collect_class_var_exports_from_body(class_path, child_body, randomizer, export_map)
            for handler in getattr(stmt, 'handlers', []):
                Obfuscator._collect_class_var_exports_from_body(class_path, handler.body, randomizer, export_map)

    @staticmethod
    def _collect_class_var_exports(file_modules, randomizer: Randomizer) -> dict:
        export_map = {}

        for file_module in file_modules:
            module_name = getattr(file_module, 'module_name', None)
            tree = getattr(file_module, 'tree', None)
            if not module_name or tree is None:
                continue

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_path = f'{module_name}.{node.name}'
                    Obfuscator._collect_class_var_exports_from_body(class_path, node.body, randomizer, export_map)

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
        charset_idx = settings.get('random_charset_index', 0)
        charset = CHARSETS[charset_idx] if 0 <= charset_idx < len(CHARSETS) else CHARSETS[0]
        randomizer.set_random_gen(n, charset)

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
            'exports': {},
            'reverse_exports': {},
            'arg_exports': {},
            'keyword_args_in_calls': set(),
            'class_vars': {},
            'vars': {},
        }

        has_function_layer = any(layer is Layer_K for layer, _ in settings['obf_layers'])
        if has_function_layer:
            randomizer.project_context['exports'] = Obfuscator._collect_project_exports(file_modules, randomizer)
            randomizer.project_context['reverse_exports'] = Obfuscator._reverse_export_map(randomizer.project_context['exports'])

        has_class_var_layer = any(layer is Layer_L for layer, _ in settings['obf_layers'])
        if has_class_var_layer:
            randomizer.project_context['class_vars'] = Obfuscator._collect_class_var_exports(file_modules, randomizer)

        has_module_var_layer = any(layer is Layer_M for layer, _ in settings['obf_layers'])
        if has_module_var_layer:
            randomizer.project_context['vars'] = Obfuscator._collect_module_var_exports(file_modules, randomizer)

        has_argument_layer = any(layer is Layer_J for layer, _ in settings['obf_layers'])
        if has_argument_layer:
            randomizer.project_context['keyword_args_in_calls'] = Obfuscator._collect_used_keyword_argument_names(file_modules)
            randomizer.project_context['arg_exports'] = Obfuscator._collect_argument_exports(
                file_modules,
                randomizer,
                randomizer.project_context['exports']
            )

        for file_module in file_modules:
            print('Obfuscating file:', file_module.in_path)
            for layer, args in settings['obf_layers']:
                print('Obfuscation layer:', layer.__name__)
                layer(randomizer, file_module, *args).visit(file_module.tree)
            out_code = unparse(file_module.tree, settings['indentation'])
            if settings['comments']:
                out_code = randomizer.generate_random_comments(out_code)
            prefix   = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n'
            post_fix = '\n# Obfuscated by *obfuspy* (Silas A. Kraume)\n'
            file_module.set_code(prefix + out_code + post_fix)
