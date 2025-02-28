"""
obfuscator
"""

import ast
import builtins
import functools
import itertools
import keyword
import os
import random
from obfuspy.util.charsets import CHARSETS

VARIABLE_LENGTH = 20#
VARIABLE_CHARSET = CHARSETS[2]#
COMMENT_LENGTH = 30
COMMENT_CHARSET = CHARSETS[3]
NUMERICAL_DENOMINATOR = 7#
DEAD_CODE_PROBABILITY = 0.1#
INDENTATION_STRING = '\t\t\t\t\t\t\t\t\t\t\t\t'#

OBFUSCATE_VARIABLE_NAMES = True#
OBFUSCATE_ARGUMENT_NAMES = True#
OBFUSCATE_FUNCTION_NAMES = True#
OBFUSCATE_CLASS_NAMES = True#
OBFUSCATE_COMMENTS = True
OBFUSCATE_NUMBERS = True#
OBFUSCATE_STRINGS = True
OBFUSCATE_DEAD_CODE = True#
OBFUSCATE_BUILTINS = True
OBFUSCATE_ANTIDEBUG = True
OBFUSCATE_INDENTATION = True#


ALL_BUILTINS = set(dir(builtins))
ALL_BUILTINS.update({
    '__annotations__',
    '__file__',
    '__path__',
})
ALL_KEYWORDS = set(keyword.kwlist + keyword.softkwlist)


def _random_name_gen(n: int, char_set: list = None):
    if char_set is None:
        char_set = CHARSETS[3]
    BUFFER_SIZE = 1_000

    def _name_gen(n: int):
        while True:
            name_gen = itertools.product(char_set, repeat=n)
            buffer = []
            for name in name_gen:
                if len(buffer) == BUFFER_SIZE:
                    yield buffer
                    buffer = []
                s_name = ''.join(name)
                if not s_name in ALL_KEYWORDS | ALL_BUILTINS:
                    buffer.append(s_name)
            yield buffer
            n += 1

    name_gen = _name_gen(n)

    while True:
        random_buffer = next(name_gen)
        random.shuffle(random_buffer)
        yield from random_buffer

@functools.lru_cache(maxsize=1_000)
def deconstruct_number(num: int) -> str:
    r = ''
    if num > NUMERICAL_DENOMINATOR:
        if num // NUMERICAL_DENOMINATOR > 1:
            if num % NUMERICAL_DENOMINATOR == 0:
                r += '(%s*%s)' % (deconstruct_number(num // NUMERICAL_DENOMINATOR), NUMERICAL_DENOMINATOR)
            else:
                r += '(%s*%s+%s)' % (deconstruct_number(num // NUMERICAL_DENOMINATOR), NUMERICAL_DENOMINATOR, num % NUMERICAL_DENOMINATOR)
        else:
            r += '(%s+%s)' % (NUMERICAL_DENOMINATOR, deconstruct_number(num - NUMERICAL_DENOMINATOR))
    else:
        r = '%s' % num
    return r


class Obfuscator:
    random_name_gen = _random_name_gen(VARIABLE_LENGTH, VARIABLE_CHARSET)
    random_cmmt_gen = _random_name_gen(COMMENT_LENGTH,  COMMENT_CHARSET )
    random_key      = random.randint(1_000, 999_999)

    def obfuscate(file_modules: set) -> None:
        obfuscator = _Obfuscator()

        for file_module in file_modules:
            in_module  = os.path.splitext(os.path.basename(file_module.in_path))[0]
            out_module = os.path.splitext(os.path.basename(file_module.out_path))[0]
            obfuscator.file_map[in_module] = out_module
            file_module.set_tree(ast.parse(file_module.in_code))

            for node in ast.walk(file_module.tree):
                if OBFUSCATE_VARIABLE_NAMES and isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    obfuscator.var_map.setdefault(node.id, next(Obfuscator.random_name_gen))
                elif OBFUSCATE_ARGUMENT_NAMES and isinstance(node, ast.arg):
                    obfuscator.var_map.setdefault(node.arg, next(Obfuscator.random_name_gen))
                elif OBFUSCATE_FUNCTION_NAMES and isinstance(node, ast.FunctionDef):
                    obfuscator.var_map.setdefault(node.name, next(Obfuscator.random_name_gen))
                elif OBFUSCATE_CLASS_NAMES and isinstance(node, ast.ClassDef):
                    obfuscator.var_map.setdefault(node.name, next(Obfuscator.random_name_gen))
        # print(obfuscator.file_map)
        # print(obfuscator.var_map)

        for file_module in file_modules:
            obfuscator.visit(file_module.tree)
            out_code = unparse(file_module.tree)
            prefix   = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n'
            post_fix = '\n\n# Obfuscated by *obfuspy* (Silas A. Kraume)\n'
            file_module.set_code(prefix + out_code + post_fix)


class Builder(ast._Unparser):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def fill(self, text=""):
        """Indent a piece of text and append it, according to the current
        indentation level"""
        self.maybe_newline()
        self.write(INDENTATION_STRING * self._indent + text)

def unparse(ast_obj):
    unparser = Builder() if OBFUSCATE_INDENTATION else ast._Unparser()
    return unparser.visit(ast_obj)


def generate_dead_classes() -> ast.stmt:
    choices = [
        # Unused class with random methods
        lambda: ast.ClassDef(
            name=next(Obfuscator.random_name_gen),
            bases=[],
            keywords=[],
            body=[generate_dead_functions() for _ in range(random.randint(1, 3))],
            decorator_list=[],
            lineno=0,
            col_offset=0
        ),
    ]
    return random.choice(choices)()

def generate_dead_functions() -> ast.stmt:
    choices = [
        # Unused function with random operations
        lambda: ast.FunctionDef(
            name=next(Obfuscator.random_name_gen),
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=next(Obfuscator.random_name_gen)) for _ in range(random.randint(1, 4))],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[generate_dead_expressions() for _ in range(random.randint(1, 4))] + [
                ast.Return(value=ast.Name(id=next(Obfuscator.random_name_gen), ctx=ast.Load()))
            ],
            decorator_list=[],
            lineno=0,
            col_offset=0
        ),
    ]
    return random.choice(choices)()

def generate_dead_expressions() -> ast.stmt:
    choices = [
        # Unused variable assignment with number
        lambda: ast.Assign(
            targets=[ast.Name(id=next(Obfuscator.random_name_gen), ctx=ast.Store())],
            value=ast.parse(deconstruct_number(random.randint(1, 1000)), mode='eval').body,
            lineno=0,
            col_offset=0
        ),
        # Unused variable assignment with string
        lambda: ast.Assign(
            targets=[ast.Name(id=next(Obfuscator.random_name_gen), ctx=ast.Store())],
            value=ast.Constant(value=''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5, 15)))),
            lineno=0,
            col_offset=0
        ),
        # Unused variable assignment with list
        lambda: ast.Assign(
            targets=[ast.Name(id=next(Obfuscator.random_name_gen), ctx=ast.Store())],
            value=ast.List(
                elts=[ast.Constant(value=random.randint(1, 100)) for _ in range(random.randint(2, 5))],
                ctx=ast.Load()
            ),
            lineno=0,
            col_offset=0
        ),
    ]
    return random.choice(choices)()

def generate_dead_code() -> ast.stmt:
    return random.choice([
        generate_dead_classes(),
        generate_dead_functions(),
        generate_dead_expressions(),
    ])


class _Obfuscator(ast.NodeTransformer):
    def __init__(self) -> None:
        self.file_map = {}
        self.var_map = {}
        self.skip_names = set(f for f in dir(builtins) if f.startswith('_'))
        self.skip_names.update({
            '__annotations__',
            '__file__',
            '__path__',
        })

    def visit_Module(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        self.generic_visit(node)
        if OBFUSCATE_DEAD_CODE:
            new_body = []
            for stmt in node.body:
                new_body.append(stmt)
                if random.random() < DEAD_CODE_PROBABILITY:
                    for _ in range(random.randint(1, 3)):
                        new_body.append(generate_dead_code())
            node.body = new_body
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
        if OBFUSCATE_DEAD_CODE:
            new_body = []
            for stmt in node.body:
                new_body.append(stmt)
                if random.random() < DEAD_CODE_PROBABILITY:
                    for _ in range(random.randint(1, 3)):
                        new_body.append(generate_dead_code())
            node.body = new_body
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
        if OBFUSCATE_DEAD_CODE:
            new_body = []
            for stmt in node.body:
                new_body.append(stmt)
                if random.random() < DEAD_CODE_PROBABILITY:
                    for _ in range(random.randint(1, 3)):
                        new_body.append(generate_dead_code())
            node.body = new_body
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
        if not OBFUSCATE_NUMBERS:
            return node
        if isinstance(node.value, int):
            if node.value == 0:
                expr_str = '(1-1)'
            else:
                expr_str = deconstruct_number(node.value)
            return ast.parse(expr_str, mode='eval').body
        elif isinstance(node.value, float):
            if node.value == 0:
                expr_str = '(1.0-1.0)'
            else:
                int_part = int(node.value)
                decimal_part = node.value - int_part
                if decimal_part == 0:
                    expr_str = deconstruct_number(int_part)
                else:
                    # Convert decimal to fraction (e.g., 0.5 -> 5/10)
                    decimal_str = str(decimal_part).split('.')[1]
                    numerator = int(decimal_str)
                    denominator = 10 ** len(decimal_str)
                    int_expr = deconstruct_number(int_part)
                    num_expr = deconstruct_number(numerator)
                    den_expr = deconstruct_number(denominator)
                    expr_str = f"({int_expr}+{num_expr}/{den_expr})"
            return ast.parse(expr_str, mode='eval').body
        return node
