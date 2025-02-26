"""
obfuscator
"""

import ast
import builtins
import functools
import itertools
import os
import random
from obfuspy.util.charsets import CHARSETS

def _random_name_gen(n: int, char_set: list = None):
    if char_set is None:
        char_set = CHARSETS[1]
    BUFFER_SIZE = 1_000

    def _name_gen(n: int):
        while True:
            name_gen = itertools.product(char_set, repeat=n)
            buffer = []
            for name in name_gen:
                if len(buffer) == BUFFER_SIZE:
                    yield buffer
                    buffer = []
                buffer.append(''.join(name))
            yield buffer
            n += 1

    name_gen = _name_gen(n)

    while True:
        random_buffer = next(name_gen)
        random.shuffle(random_buffer)
        yield from random_buffer

@functools.lru_cache(maxsize=1_000)
def number_deconstructor(num: int, denominator: int) -> str:
    r = ''
    if num > denominator:
        if num // denominator > 1:
            if num % denominator == 0:
                r += '(%s*%s)' % (number_deconstructor(num // denominator, denominator), denominator)
            else:
                r += '(%s*%s+%s)' % (number_deconstructor(num // denominator, denominator), denominator, num % denominator)
        else:
            r += '(%s+%s)' % (denominator, number_deconstructor(num - denominator, denominator))
    else:
        r = '%s' % num
    return r


class Obfuscator:
    def obfuscate(file_modules: set) -> None:
        obfuscator = _Obfuscator()
        random_gen = _random_name_gen(5)

        for file_module in file_modules:
            in_module  = os.path.splitext(os.path.basename(file_module.in_path))[0]
            out_module = os.path.splitext(os.path.basename(file_module.out_path))[0]
            obfuscator.file_map[in_module] = out_module
            file_module.set_tree(ast.parse(file_module.in_code))

            for node in ast.walk(file_module.tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    obfuscator.var_map.setdefault(node.id, next(random_gen))
                elif isinstance(node, ast.arg):
                    obfuscator.var_map.setdefault(node.arg, next(random_gen))
                elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    obfuscator.var_map.setdefault(node.name, next(random_gen))


        print(obfuscator.file_map)

        for file_module in file_modules:
            obfuscator.visit(file_module.tree)
            out_code = ast.unparse(file_module.tree)
            prefix   = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n'
            post_fix = '\n\n# Obfuscated by *obfuspy* (Silas A. Kraume)\n'
            file_module.set_code(prefix + out_code + post_fix)



class _Obfuscator(ast.NodeTransformer):
    def __init__(self) -> None:
        self.file_map = {}
        self.var_map = {}
        self.skip_names = set(dir(builtins))
        self.skip_names.update({
            '__annotations__',
            '__file__',
            '__path__',

            '__name__',
            '__package__',
            '__spec__',
            '__doc__',
        })
        self.numerical_denominator = 7

    def visit_Module(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Str)):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    def visit_Import(self, node):
        for name in node.names:
            if name.name in self.file_map:
                name.name = self.file_map[name.name]
        return node

    def visit_ImportFrom(self, node):
        if node.level == 0: # absolute import
            if node.module in self.file_map:
                node.module = self.file_map[node.module]
        else: # relative imports
            # For relative imports, module might be None for "from .. import x"
            if node.module:
                parts = node.module.split('.')
                if parts[-1] in self.file_map:
                    parts[-1] = self.file_map[parts[-1]]
                    node.module = '.'.join(parts)

        for name in node.names:
            if name.name in self.var_map:
                name.name = self.var_map[name.name]

        return node

    def visit_ClassDef(self, node):
        if node.name in self.skip_names:
            return node
        if node.name in self.var_map:
            node.name = self.var_map[node.name]
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Str)):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        if node.name in self.skip_names:
            return node
        if node.name in self.var_map:
            node.name = self.var_map[node.name]
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Str)):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)

        current = node
        root = None
        while isinstance(current, ast.Attribute):
            current = current.value
            if isinstance(current, ast.Name):
                root = current
                break

        if root and root.id in self.file_map:
            root.id = self.file_map[root.id]
        if node.attr in self.var_map:
            node.attr = self.var_map[node.attr]

        return node

    def visit_Name(self, node):
        if node.id in self.skip_names:
            return node

        if node.id in self.var_map:
            node.id = self.var_map[node.id]
        return node

    def visit_arg(self, node):
        if node.arg in self.var_map:
            node.arg = self.var_map[node.arg]
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, int):
            if node.value == 0:
                expr_str = '(1-1)'
            else:
                expr_str = number_deconstructor(node.value, self.numerical_denominator)
            return ast.parse(expr_str, mode='eval').body
        elif isinstance(node.value, float):
            if node.value == 0:
                expr_str = '(1.0-1.0)'
            else:
                int_part = int(node.value)
                decimal_part = node.value - int_part
                if decimal_part == 0:
                    expr_str = number_deconstructor(int_part, self.numerical_denominator)
                else:
                    # Convert decimal to fraction (e.g., 0.5 -> 5/10)
                    decimal_str = str(decimal_part).split('.')[1]
                    numerator = int(decimal_str)
                    denominator = 10 ** len(decimal_str)
                    int_expr = number_deconstructor(int_part, self.numerical_denominator)
                    num_expr = number_deconstructor(numerator, self.numerical_denominator)
                    den_expr = number_deconstructor(denominator, self.numerical_denominator)
                    expr_str = f"({int_expr}+{num_expr}/{den_expr})"
            return ast.parse(expr_str, mode='eval').body
        return node
