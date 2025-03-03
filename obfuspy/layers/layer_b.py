import ast
from obfuspy.util.randomizer import Randomizer


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


class Layer_B(ast.NodeTransformer):
    """
    Layer B obfuscates string constants in the AST.
    """
    def __init__(self, randomizer: Randomizer) -> None:
        self.randomizer = randomizer

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
            f"{self.randomizer.random_str_name}=lambda s: str().join(chr(ord(c)^{self.randomizer.random_str_key}) for c in s)"
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

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.Call(
                func=ast.Name(id=self.randomizer.random_str_name, ctx=ast.Load()),
                args=[ast.Constant(
                    value=''.join(chr(ord(c) ^ self.randomizer.random_str_key) for c in node.value)
                )],
                keywords=[],
            )
        return node
