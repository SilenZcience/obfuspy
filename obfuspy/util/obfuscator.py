"""
obfuscator
"""

import ast
import os
import symtable

from obfuspy.layers.obfAntiTampering import ObfAntiTampering
from obfuspy.layers.obfBuiltins import ObfBuiltins
from obfuspy.layers.obfClassNames import ObfClassNames
from obfuspy.layers.obfClassVariables import ObfClassVariables
from obfuspy.layers.obfDefArguments import ObfDefArguments
from obfuspy.layers.obfDefNames import ObfDefnames
from obfuspy.layers.obfImports import ObfImports
from obfuspy.layers.obfLocalVariables import ObfLocalVariables
from obfuspy.layers.obfModuleVariables import ObfModuleVariables
from obfuspy.layers.obfNumericalConstants import ObfNumericalConstants
from obfuspy.layers.obfStringConstants import ObfStringConstants
from obfuspy.util.charsets import CHARSETS
from obfuspy.util.domain import SYMBOL_MAP, Node
from obfuspy.util.randomizer import ALL_BUILTINS, Randomizer
from obfuspy.util.unparser import unparse

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
    def _collect_obj_defs(file_modules, randomizer: Randomizer) -> None:
        def is_valid_insert(prefix_parts: list) -> None:
            part_name = prefix_parts[-1].name if prefix_parts else ''
            # if part_name.startswith('__') and part_name.endswith('__'):
            #     return False
            if part_name in ALL_BUILTINS:
                return False
            return True

        def walk(node, prefix_parts: list) -> None:
            if isinstance(node, ast.ClassDef):
                class_parts = [*prefix_parts, Node.Cls(node.name)]
                if is_valid_insert(class_parts):
                    SYMBOL_MAP.insert(class_parts, {
                        'name': next(randomizer.random_name_gen),
                    })
                for child in node.body:
                    walk(child, class_parts)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_parts = [*prefix_parts, Node.Def(node.name)]
                if is_valid_insert(function_parts):
                    SYMBOL_MAP.insert(function_parts, {
                        'name': next(randomizer.random_name_gen),
                    })
                for child in node.body:
                    walk(child, function_parts)
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

            prefix_parts = [Node.Module(module_name)]
            SYMBOL_MAP.insert(prefix_parts, {'name': module_name})

            for node in tree.body:
                walk(node, prefix_parts)

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
    def _collect_module_vars_from_body(body: list, prefix_parts: list, randomizer: Randomizer) -> None:
        def is_valid_insert(name: str) -> None:
            if name.startswith('__') and name.endswith('__'):
                return False
            if name in ALL_BUILTINS:
                return False
            return True

        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    for name in Obfuscator._collect_target_names(target):
                        if is_valid_insert(name):
                            SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                                'name': next(randomizer.random_name_gen),
                            })
            elif isinstance(stmt, ast.AnnAssign):
                for name in Obfuscator._collect_target_names(stmt.target):
                    if is_valid_insert(name):
                        SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                            'name': next(randomizer.random_name_gen),
                        })
            elif isinstance(stmt, ast.AugAssign):
                for name in Obfuscator._collect_target_names(stmt.target):
                    if is_valid_insert(name):
                        SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                            'name': next(randomizer.random_name_gen),
                        })
            elif isinstance(stmt, ast.With):
                for item in stmt.items:
                    if item.optional_vars is not None:
                        for name in Obfuscator._collect_target_names(item.optional_vars):
                            if is_valid_insert(name):
                                SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                                    'name': next(randomizer.random_name_gen),
                                })
            elif isinstance(stmt, ast.AsyncWith):
                for item in stmt.items:
                    if item.optional_vars is not None:
                        for name in Obfuscator._collect_target_names(item.optional_vars):
                            if is_valid_insert(name):
                                SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                                    'name': next(randomizer.random_name_gen),
                                })
            elif isinstance(stmt, ast.For):
                for name in Obfuscator._collect_target_names(stmt.target):
                    if is_valid_insert(name):
                        SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                            'name': next(randomizer.random_name_gen),
                        })
            elif isinstance(stmt, ast.AsyncFor):
                for name in Obfuscator._collect_target_names(stmt.target):
                    if is_valid_insert(name):
                        SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(name)], {
                            'name': next(randomizer.random_name_gen),
                        })
            elif isinstance(stmt, ast.Try):
                for handler in stmt.handlers:
                    if handler.name and isinstance(handler.name, str):
                        if is_valid_insert(handler.name):
                            SYMBOL_MAP.insert([*prefix_parts, Node.ModVar(handler.name)], {
                                'name': next(randomizer.random_name_gen),
                            })

            for field_name in ('body', 'orelse', 'finalbody'):
                child_body = getattr(stmt, field_name, None)
                if child_body:
                    Obfuscator._collect_module_vars_from_body(child_body, prefix_parts, randomizer)
            for handler in getattr(stmt, 'handlers', []):
                Obfuscator._collect_module_vars_from_body(handler.body, prefix_parts, randomizer)

    @staticmethod
    def _collect_module_vars(file_modules, randomizer: Randomizer) -> None:
        for file_module in file_modules:
            module_name = getattr(file_module, 'module_name', None)
            tree = getattr(file_module, 'tree', None)
            if not module_name or tree is None:
                continue

            prefix_parts = [Node.Module(module_name)]
            SYMBOL_MAP.insert(prefix_parts, {'name': module_name})

            Obfuscator._collect_module_vars_from_body(tree.body, prefix_parts, randomizer)

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
    def _collect_class_vars(file_modules, randomizer: Randomizer) -> None:
        def collect_in_class_body(prefix_parts: list, body: list) -> None:
            for stmt in body:

                if isinstance(stmt, ast.ClassDef):
                    class_parts = [*prefix_parts, Node.Cls(stmt.name)]
                    collect_in_class_body(class_parts, stmt.body)
                    continue

                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_parts = [*prefix_parts, Node.Def(stmt.name)]
                    for child in stmt.body:
                        walk(child, function_parts)
                    continue

                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        for name in Obfuscator._collect_target_names(target):
                            SYMBOL_MAP.insert([*prefix_parts, Node.ClassVar(name)], {
                                'name': next(randomizer.random_name_gen)
                            })
                elif isinstance(stmt, ast.AnnAssign):
                    for name in Obfuscator._collect_target_names(stmt.target):
                        SYMBOL_MAP.insert([*prefix_parts, Node.ClassVar(name)], {
                            'name': next(randomizer.random_name_gen)
                        })
                elif isinstance(stmt, ast.AugAssign):
                    for name in Obfuscator._collect_target_names(stmt.target):
                        SYMBOL_MAP.insert([*prefix_parts, Node.ClassVar(name)], {
                            'name': next(randomizer.random_name_gen)
                        })

                for field_name in ('body', 'orelse', 'finalbody'):
                    child_body = getattr(stmt, field_name, None)
                    if child_body:
                        collect_in_class_body(prefix_parts, child_body)
                for handler in getattr(stmt, 'handlers', []):
                    collect_in_class_body(prefix_parts, handler.body)

        def walk(node, prefix_parts: list) -> None:
            if isinstance(node, ast.ClassDef):
                class_parts = [*prefix_parts, Node.Cls(node.name)]
                collect_in_class_body(class_parts, node.body)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_parts = [*prefix_parts, Node.Def(node.name)]
                for child in node.body:
                    walk(child, function_parts)
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

            prefix_parts = [Node.Module(module_name)]

            for node in tree.body:
                walk(node, prefix_parts)

    @staticmethod
    def _collect_argument_exports(file_modules, randomizer: Randomizer) -> None:
        keyword_blocklist = Obfuscator._collect_used_keyword_argument_names(file_modules)

        def is_valid_insert(arg_node) -> None:
            if arg_node is None:
                return False
            if arg_node.arg.startswith('__') and arg_node.arg.endswith('__'):
                return False
            if arg_node.arg in ALL_BUILTINS:
                return False
            if arg_node.arg in keyword_blocklist:
                return False
            return True

        def walk(node, prefix_parts: list) -> None:
            if isinstance(node, ast.ClassDef):
                class_parts = [*prefix_parts, Node.Cls(node.name)]
                for child in node.body:
                    walk(child, class_parts)
                return

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_parts = [*prefix_parts, Node.Def(node.name)]

                args_node = node.args
                for arg in getattr(args_node, 'posonlyargs', []):
                    if is_valid_insert(arg):
                        SYMBOL_MAP.insert([*function_parts, Node.DefArg(arg.arg)], {
                            'name': next(randomizer.random_name_gen),
                        })
                for arg in getattr(args_node, 'args', []):
                    if is_valid_insert(arg):
                        SYMBOL_MAP.insert([*function_parts, Node.DefArg(arg.arg)], {
                            'name': next(randomizer.random_name_gen),
                        })
                for arg in getattr(args_node, 'kwonlyargs', []):
                    if is_valid_insert(arg):
                        SYMBOL_MAP.insert([*function_parts, Node.DefArg(arg.arg)], {
                            'name': next(randomizer.random_name_gen),
                        })
                if is_valid_insert(getattr(args_node, 'vararg', None)):
                    SYMBOL_MAP.insert([*function_parts, Node.DefArg(args_node.vararg.arg)], {
                        'name': next(randomizer.random_name_gen),
                    })
                if is_valid_insert(getattr(args_node, 'kwarg', None)):
                    SYMBOL_MAP.insert([*function_parts, Node.DefArg(args_node.kwarg.arg)], {
                        'name': next(randomizer.random_name_gen),
                    })

                for child in node.body:
                    walk(child, function_parts)
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

            prefix_parts = [Node.Module(module_name)]

            for node in tree.body:
                walk(node, prefix_parts)

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

        has_function_layer =   any(layer is ObfDefnames        for layer, _ in settings['obf_layers'])
        has_class_layer =      any(layer is ObfClassNames      for layer, _ in settings['obf_layers'])
        has_class_var_layer =  any(layer is ObfClassVariables  for layer, _ in settings['obf_layers'])
        has_module_var_layer = any(layer is ObfModuleVariables for layer, _ in settings['obf_layers'])
        has_argument_layer =   any(layer is ObfDefArguments    for layer, _ in settings['obf_layers'])
        randomizer.project_context = {
            'root_path': common_root,
            'module_names': {file_module.in_path: file_module.module_name for file_module in file_modules},
            'enabled_layers': {
                'functions': has_function_layer,
                'classes': has_class_layer,
                'class_vars': has_class_var_layer,
                'module_vars': has_module_var_layer,
                'arguments': has_argument_layer,
            },
            # 'defined_names': Obfuscator._collect_defined_names(file_modules), # only so that builints does not overwrite. builtins should do this on its own when necceseary
            # 'keyword_args_in_calls': set(),
        }
        SYMBOL_MAP.set_randomizer(randomizer)

        Obfuscator._collect_obj_defs(
            file_modules,
            randomizer,
        )
        Obfuscator._collect_module_vars(
            file_modules,
            randomizer,
        )
        Obfuscator._collect_class_vars(
            file_modules,
            randomizer,
        )
        Obfuscator._collect_argument_exports(
            file_modules,
            randomizer,
        )

        for layer, args in settings['obf_layers']:
            print('Applying obfuscation layer:', layer.__name__)
            for file_module in file_modules:
                try:
                    l = layer(randomizer, file_module, *args)
                    l.visit(file_module.tree)
                except Exception as e:
                    raise Exception(f"Failed to apply layer {layer.__name__} to file {file_module.in_path}") from e
                print('.', end='', flush=True)
                if any(isinstance(l, obfLayer) for obfLayer in (ObfStringConstants, ObfNumericalConstants, ObfBuiltins)):
                    ObfAntiTampering.HASH_NODES[file_module] = {k: v+[l] for k, v in ObfAntiTampering.HASH_NODES.get(file_module, {}).items()}
            print()
            layer.FIRST_PASS = False


        print('Finalizing files')
        for file_module in file_modules:
            try:
                out_code = unparse(file_module.tree, settings['indentation'])

                if settings['random_comment_length']:
                    rnd_cmt_list = list(randomizer.generate_random_comments(out_code))
                    file_module_lines = out_code.split('\n')
                    for i, (_, rnd_cmt) in enumerate(zip(file_module_lines, rnd_cmt_list)):
                        file_module_lines[i] += f"#{rnd_cmt}"
                    out_code = '\n'.join(file_module_lines)

                out_code = prefix + out_code + post_fix
                out_code = ObfAntiTampering.finalize_hash_nodes(out_code, file_module)
            except Exception as e:
                raise Exception(f"Failed to finalize file {file_module.in_path}") from e
            print('.', end='', flush=True)

            file_module.set_code(out_code)
        print()
