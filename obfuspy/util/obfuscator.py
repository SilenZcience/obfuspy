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

VARIABLE_LENGTH = 5
VARIABLE_CHARSET = CHARSETS[0]
COMMENT_LENGTH = 1
COMMENT_CHARSET = CHARSETS[0]
NUMERICAL_DENOMINATOR = 8
DEAD_CODE_PROBABILITY = 0.3
ANTI_DEBUG_PROBABILITY = 0.2
INDENTATION_STRING = '\t\t\t'

OBFUSCATE_VARIABLE_NAMES = False
OBFUSCATE_ARGUMENT_NAMES = False
OBFUSCATE_FUNCTION_NAMES = False
OBFUSCATE_CLASS_NAMES = False
OBFUSCATE_COMMENTS = False
OBFUSCATE_NUMBERS = False
OBFUSCATE_STRINGS = False
OBFUSCATE_DEAD_CODE = False
OBFUSCATE_BUILTINS = True
OBFUSCATE_ANTIDEBUG = False
OBFUSCATE_INDENTATION = False
OBFUSCATE_ANNOTATIONS = True

BUILTINS_DEFAULT = set(f for f in dir(builtins) if not f.startswith('_'))
BUILTINS_DUNDER = set(f for f in dir(builtins) if f.startswith('_'))
# BUILTINS_DUNDER.update({
#     '__annotations__',
#     '__file__',
#     '__path__',
# })
KEYWORDS_VAL = {'True', 'False', 'None'}
ALL_BUILTINS = BUILTINS_DEFAULT | BUILTINS_DUNDER | KEYWORDS_VAL
ALL_KEYWORDS = set(keyword.kwlist + keyword.softkwlist)


def _random_name_gen(n: int, char_set: list = None):
    if char_set is None:
        char_set = CHARSETS[3]
    buffer_size = 1_000

    def _name_gen(n: int):
        while True:
            name_gen = itertools.product(char_set, repeat=n)
            buffer = []
            for name in name_gen:
                if len(buffer) == buffer_size:
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
                r += f"({deconstruct_number(num // NUMERICAL_DENOMINATOR)}*{NUMERICAL_DENOMINATOR})"
            else:
                r += f"({deconstruct_number(num // NUMERICAL_DENOMINATOR)}*{NUMERICAL_DENOMINATOR}+{num % NUMERICAL_DENOMINATOR})"
        else:
            r += f"({NUMERICAL_DENOMINATOR}+{deconstruct_number(num - NUMERICAL_DENOMINATOR)})"
    else:
        r = f"{num}"
    return r

def generate_random_comments(code: str) -> str:
    lines = code.split('\n')
    for i, _ in enumerate(lines):
        if lines[i].strip():
            lines[i] += f"#{next(Obfuscator.random_cmmt_gen)}"
        else:
            lines[i] = f"#{random.choice(lines)}"
    return '\n'.join(lines)


class Obfuscator:
    random_name_gen = _random_name_gen(VARIABLE_LENGTH, VARIABLE_CHARSET)
    random_cmmt_gen = _random_name_gen(COMMENT_LENGTH,  COMMENT_CHARSET )
    random_str_key  = random.randint(1_000, 999_999)
    random_str_name = 'deobfuscate_string'

    @staticmethod
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
                elif OBFUSCATE_FUNCTION_NAMES and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    obfuscator.var_map.setdefault(node.name, next(Obfuscator.random_name_gen))
                elif OBFUSCATE_CLASS_NAMES and isinstance(node, ast.ClassDef):
                    obfuscator.var_map.setdefault(node.name, next(Obfuscator.random_name_gen))
        print(obfuscator.file_map)
        # print(obfuscator.var_map)

        Obfuscator.random_str_name = next(Obfuscator.random_name_gen)
        obfuscator.var_map.setdefault(Obfuscator.random_str_name, Obfuscator.random_str_name)
        obfuscator.var_map.setdefault('s', next(Obfuscator.random_name_gen))
        obfuscator.var_map.setdefault('c', next(Obfuscator.random_name_gen)) # the vars we use in the string deobfuscator
        if OBFUSCATE_BUILTINS:
            for builtin in ALL_BUILTINS:
                obfuscator.var_map.setdefault(builtin, next(Obfuscator.random_name_gen))

        for file_module in file_modules:
            obfuscator.visit(file_module.tree)
            out_code = unparse(file_module.tree)
            if OBFUSCATE_COMMENTS:
                out_code = generate_random_comments(out_code)
            prefix   = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n'
            post_fix = '\n# Obfuscated by *obfuspy* (Silas A. Kraume)\n'
            file_module.set_code(prefix + out_code + post_fix)


class Builder(ast._Unparser):
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
    random_args = [next(Obfuscator.random_name_gen) for _ in range(random.randint(1, 4))]
    choices = [
        # Unused function with random operations
        lambda: ast.FunctionDef(
            name=next(Obfuscator.random_name_gen),
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=random_arg) for random_arg in random_args],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[generate_dead_expressions() for _ in range(random.randint(1, 4))] + [
                ast.Return(value=ast.Name(id=random.choice(random_args), ctx=ast.Load()))
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
            value=ast.parse(str(random.randint(1, 9_999_999)), mode='eval').body,
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

def generate_str_deobfuscator_code() -> ast.stmt:
    return ast.parse(
        f"{Obfuscator.random_str_name} = lambda s: str().join(chr(ord(c)^{Obfuscator.random_str_key}) for c in s)"
    ).body

def generate_anti_debug_code() -> ast.stmt:
    offset = random.randint(2, 4)
    anti_debug_stmt = 'import sys;sys.exit(0) if sys.gettrace() is not None else None'
    anti_debug_stmt = ''.join(c + ''.join(random.choice(CHARSETS[0]) for _ in range(offset-1)) for c in anti_debug_stmt)
    return ast.parse(f"exec('{anti_debug_stmt}'[::{offset}])").body

def generate_builtin_code(var_map: dict) -> list:
    return ast.Assign(
        targets=[ast.Tuple(
            elts=[ast.Name(id=var_map[b], ctx=ast.Store()) for b in ALL_BUILTINS],
            ctx=ast.Store()
        )],
        value=ast.Tuple(
            elts=[ast.Name(id=b, ctx=ast.Load()) for b in ALL_BUILTINS],
            ctx=ast.Load()
        ),
        lineno=0,
        col_offset=0
    )

def generate_annotation_code() -> list:
    choices = [
        lambda: ast.Name(id='None',  ctx=ast.Load()),
        lambda: ast.Name(id='int',   ctx=ast.Load()),
        lambda: ast.Name(id='str',   ctx=ast.Load()),
        lambda: ast.Name(id='float', ctx=ast.Load()),
        lambda: ast.Name(id='bool',  ctx=ast.Load()),
        lambda: ast.Name(id='dict',  ctx=ast.Load()),
        lambda: ast.Name(id='list',  ctx=ast.Load()),
        lambda: ast.Name(id='tuple', ctx=ast.Load()),
        lambda: ast.Name(id='set',   ctx=ast.Load()),
    ]
    return random.choice(choices)()

class _Obfuscator(ast.NodeTransformer):
    def __init__(self) -> None:
        self.file_map = {}
        self.var_map = {}
        self.skip_names = ALL_KEYWORDS-KEYWORDS_VAL if OBFUSCATE_BUILTINS else ALL_BUILTINS|ALL_KEYWORDS

    def visit_Module(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        insert_position = 0
        for i, stmt in enumerate(node.body):
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                insert_position = i
                break
        if OBFUSCATE_ANTIDEBUG:
            node.body[insert_position:insert_position] = generate_anti_debug_code()
            for i in sorted(random.sample(range(insert_position+1,len(node.body)+1), int((len(node.body)-insert_position) * ANTI_DEBUG_PROBABILITY)), reverse=True):
                node.body[i:i] = generate_anti_debug_code()
        if OBFUSCATE_STRINGS:
            node.body[insert_position:insert_position] = generate_str_deobfuscator_code()
        if OBFUSCATE_DEAD_CODE:
            for i in sorted(random.sample(range(insert_position+1,len(node.body)+1), int((len(node.body)-insert_position) * DEAD_CODE_PROBABILITY)), reverse=True):
                node.body.insert(i, generate_dead_code())
        self.generic_visit(node)
        if OBFUSCATE_BUILTINS:
            node.body.insert(insert_position, generate_builtin_code(self.var_map))
        return node

    def visit_Import(self, node):
        for name in node.names:
            # print("Import:", name.name, name.asname)
            if name.name in self.file_map:
                name.name = self.file_map[name.name]
        return node

    def visit_ImportFrom(self, node):
        # TODO: fix import from
        # print("ImportFrom:", node.module, node.names)
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
            # print(name.name, name.asname)
            if name.name in self.var_map:
                name.name = self.var_map[name.name]

        return node

    def visit_ClassDef(self, node):
        if node.name in self.skip_names:
            return node
        if node.name in self.var_map:
            node.name = self.var_map[node.name]
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        if OBFUSCATE_DEAD_CODE:
            new_body = []
            for stmt in node.body:
                new_body.append(stmt)
                if random.random() < DEAD_CODE_PROBABILITY:
                    for _ in range(random.randint(1, 3)):
                        new_body.append(generate_dead_functions())
            node.body = new_body
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        if node.name in self.skip_names:
            return node
        if node.name in self.var_map:
            node.name = self.var_map[node.name]
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        if OBFUSCATE_DEAD_CODE:
            new_body = []
            for stmt in node.body:
                new_body.append(stmt)
                if random.random() < DEAD_CODE_PROBABILITY:
                    for _ in range(random.randint(1, 3)):
                        new_body.append(generate_dead_expressions())
            node.body = new_body
        self.generic_visit(node)
        if OBFUSCATE_ANNOTATIONS:
            for arg in node.args.args:
                arg.annotation = generate_annotation_code()
            node.returns = generate_annotation_code()
        return node

    def visit_AsyncFunctionDef(self, node):
        if node.name in self.skip_names:
            return node
        if node.name in self.var_map:
            node.name = self.var_map[node.name]
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        if OBFUSCATE_DEAD_CODE:
            new_body = []
            for stmt in node.body:
                new_body.append(stmt)
                if random.random() < DEAD_CODE_PROBABILITY:
                    for _ in range(random.randint(1, 3)):
                        new_body.append(generate_dead_expressions())
            node.body = new_body
        self.generic_visit(node)
        if OBFUSCATE_ANNOTATIONS:
            for arg in node.args.args:
                arg.annotation = generate_annotation_code()
            node.returns = generate_annotation_code()
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

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        if OBFUSCATE_ANNOTATIONS:
            node.annotation = generate_annotation_code()
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

    def visit_JoinedStr(self, node):
        self.generic_visit(node)
        return ast.Call(
            func=ast.Attribute(
                value=ast.Constant(value=''),
                attr='join',
                ctx=ast.Load()
            ),
            args=[ast.List(elts=node.values, ctx=ast.Load())],
            keywords=[]
        )

    def visit_FormattedValue(self, node):
        self.generic_visit(node)
        return ast.Call(
            func=ast.Name(id='str', ctx=ast.Load()),
            args=[node.value],
            keywords=[]
        )

    def visit_Constant(self, node):
        if OBFUSCATE_BUILTINS and isinstance(node.value, (bool, type(None))):
            return ast.Name(id=self.var_map[str(node.value)], ctx=ast.Load())
        if OBFUSCATE_NUMBERS and isinstance(node.value, int):
            if node.value == 0:
                expr_str = '(1-1)'
            else:
                expr_str = deconstruct_number(node.value)
            return ast.parse(expr_str, mode='eval').body
        if OBFUSCATE_NUMBERS and isinstance(node.value, float):
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
        if OBFUSCATE_STRINGS and isinstance(node.value, str):
            return ast.Call(
                func=ast.Name(id=Obfuscator.random_str_name, ctx=ast.Load()),
                args=[ast.Constant(value=''.join(chr(ord(c) ^ Obfuscator.random_str_key) for c in node.value))],
                keywords=[],
            )
        return node
