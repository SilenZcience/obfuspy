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

class ObfStringConstants(ast.NodeTransformer):
    """
    Obfuscates string constants.
    """

    def __init__(self, randomizer: Randomizer, _) -> None:
        self.randomizer = randomizer

    def visit_Module(self, node):
        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
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
        if node.format_spec is None:
            return ast.Call(
                func=ast.Name(id='str', ctx=ast.Load()),
                args=[self.visit(node.value)],
                keywords=[]
            )
        return ast.JoinedStr(
            values=[
                ast.FormattedValue(
                    value=self.visit(node.value),
                    conversion=node.conversion,
                    format_spec=node.format_spec
                )
            ]
        )

    @staticmethod
    def generate_obfuscated_ast_node(s: str, randomizer):
        key = sum(map(ord, s)) & 0xff
        rint = random.randint(10,100)
        value = ''.join(
            chr(ord(c) ^ ((key ^ (i * rint)) & 0xff))
            for i, c in enumerate(s)
        )
        ridx = random.randint(0, len(s))
        value = value[:ridx] + chr(key) + value[ridx:]
        tmp_value0 = next(randomizer.random_name_gen)
        tmp_value1 = next(randomizer.random_name_gen)
        tmp_value2 = next(randomizer.random_name_gen)
        return ast.parse(
            f"(lambda {tmp_value0}: str().join(chr(ord({tmp_value2})^((ord({tmp_value0}[{ridx}])^({tmp_value1}*{rint}))&0xff)) for {tmp_value1},{tmp_value2} in enumerate({tmp_value0}[:{ridx}]+{tmp_value0}[{ridx+1}:])))({value!r})",
            mode='eval'
        ).body

    @staticmethod
    def generate_compressed_logic(s: str, randomizer):
        compressed = unicode_compress(s.encode('utf-8'))
        decompressed = unicode_decompress(compressed)
        if decompressed != s:
            raise ValueError
        tmp_value0 = next(randomizer.random_name_gen)
        tmp_value1 = next(randomizer.random_name_gen)
        return ast.parse(
            f"str().join(chr((({tmp_value0}<<6&64|{tmp_value1}&63)+22)%133+10) for {tmp_value0},{tmp_value1} in zip(*(iter({compressed!r}),)*2))",
            mode='eval'
        ).body

    @staticmethod
    def obf_string_node(node, randomizer):
        if random.random() < 0.7:
            return ObfStringConstants.generate_obfuscated_ast_node(node.value, randomizer)
        try:
            return ObfStringConstants.generate_compressed_logic(node.value, randomizer)
        except ValueError:
            return ObfStringConstants.generate_obfuscated_ast_node(node.value, randomizer)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            if node.value == ';;REPLACEMEHASH':
                return node
            return self.obf_string_node(node, self.randomizer)
        return node
