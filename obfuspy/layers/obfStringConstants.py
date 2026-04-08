import ast
import random
from obfuspy.util.randomizer import Randomizer


def unicode_compress(bytes):
    o = bytearray()
    for c in bytes:
        if c < 32 or c > 126:
            raise ValueError
        # Code point translation
        v = (c-11)%133-21
        o += ((v >> 6) & 1 | 0b11001100).to_bytes(1,'big')
        o += ((v & 63) | 0b10000000).to_bytes(1,'big')
    return o

def unicode_decompress(b):
    return str().join(chr(((h<<6&64|c&63)+22)%133+10) for h,c in zip(*(iter(b),)*2))


class StringUsageFinder(ast.NodeVisitor):
    """
    Fast visitor to find first string usage in AST
    """
    def __init__(self):
        self.uses_strings = False

    def generic_visit(self, node):
        if not self.uses_strings:
            super().generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.uses_strings = True

    def visit_JoinedStr(self, _):
        self.uses_strings = True

    def visit_FormattedValue(self, _):
        self.uses_strings = True

    def check_node(self, node):
        self.visit(node)
        return self.uses_strings


class ObfStringConstants(ast.NodeTransformer):
    """
    Obfuscates string constants.
    """
    def __init__(self, randomizer: Randomizer, _) -> None:
        self.randomizer = randomizer
        self.random_str_name = next(randomizer.random_name_gen)

    def visit_Module(self, node):
        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
        finder = StringUsageFinder()
        insert_position = len(node.body)
        for i, stmt in enumerate(node.body):
            if isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) or \
            finder.check_node(stmt):
                insert_position = i
                break
        node.body[insert_position:insert_position] = ast.parse(
            f"{self.random_str_name}=lambda s: str().join(chr(ord(c)^((ord(s[0])^(i*31))&0xff)) for i,c in enumerate(s[1:]))"
        ).body
        self.generic_visit(node)
        if doc_string:
            node.body.insert(0, doc_string)
        return node

    def visit_ClassDef(self, node):
        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
        self.generic_visit(node)
        if doc_string:
            node.body.insert(0, doc_string)
        return node

    def visit_FunctionDef(self, node):
        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
        self.generic_visit(node)
        if doc_string:
            node.body.insert(0, doc_string)
        return node

    def visit_AsyncFunctionDef(self, node):
        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
        self.generic_visit(node)
        if doc_string:
            node.body.insert(0, doc_string)
        return node

    def visit_JoinedStr(self, node):
        self.generic_visit(node)
        return ast.Call(
            func=ast.Attribute(
                value=self.visit(ast.Constant(value='')),
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

    def generate_obfuscated_ast_node(self, s: str):
        key = sum(map(ord, s)) & 0xff
        value = chr(key) + ''.join(
            chr(ord(c) ^ ((key ^ (i * 31)) & 0xff))
            for i, c in enumerate(s)
        )
        return ast.Call(
            func=ast.Name(id=self.random_str_name, ctx=ast.Load()),
            args=[ast.Constant(
                value=value
            )],
            keywords=[],
        )

    def generate_compressed_logic(self, s: str):
        compressed = unicode_compress(s.encode('utf-8'))
        decompressed = unicode_decompress(compressed)
        if decompressed != s:
            raise ValueError
        return ast.parse(f"str().join(chr(((h<<6&64|c&63)+22)%133+10) for h,c in zip(*(iter({compressed!r}),)*2))", mode='eval').body

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            if random.random() < 0.7:
                return self.generate_obfuscated_ast_node(node.value)
            try:
                return self.generate_compressed_logic(node.value)
            except ValueError:
                return self.generate_obfuscated_ast_node(node.value)

        return node
