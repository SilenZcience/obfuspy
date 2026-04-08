import ast
from obfuspy.util.randomizer import Randomizer, ALL_BUILTINS


class ObfBuiltins(ast.NodeTransformer):
    """
    Obfuscates builtins.
    """
    def __init__(self, randomizer: Randomizer, _) -> None:
        self.randomizer = randomizer
        self.builtin_map = {b: next(self.randomizer.random_name_gen) for b in ALL_BUILTINS}

    def builtin_code(self, lineno=1):
        value = ','.join(map(str, self.builtin_map.values()))
        value += '='
        value += ','.join(map(str, self.builtin_map.keys()))
        node = ast.Expr(
            value=ast.Call(
                func=ast.Name(id='exec', ctx=ast.Load()),
                args=[ast.Constant(value=value)],
                keywords=[]
            )
        )
        return node

    def visit_Module(self, node):
        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
        insert_position = 0
        for i, n in enumerate(node.body):
            if not isinstance(n, (ast.Import, ast.ImportFrom)):
                insert_position = i
                break
        self.generic_visit(node)
        node.body.insert(insert_position, self.builtin_code())
        if doc_string:
            node.body.insert(0, doc_string)
        return node

    def visit_Name(self, node):
        # parent = getattr(node, '_parent', None)
        # if (
        #     (isinstance(parent, (ast.AnnAssign, ast.arg)) and parent.annotation is node) or
        #     (isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and parent.returns is node) or
        #     (isinstance(parent, ast.Call) and
        #     isinstance(parent.func, ast.Name) and
        #     parent.func.id in ('TypeVar', 'NewType'))
        # ):
        #     return node
        if node.id in self.builtin_map:
            return ast.Name(
                id=self.builtin_map[node.id],
                ctx=node.ctx
            )
        return node

    def visit_Constant(self, node):
        # parent = getattr(node, '_parent', None)
        # if (
        #     (isinstance(parent, (ast.AnnAssign, ast.arg)) and parent.annotation is node) or
        #     (isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and parent.returns is node) or
        #     (isinstance(parent, ast.Call) and
        #     isinstance(parent.func, ast.Name) and
        #     parent.func.id in ('TypeVar', 'NewType'))
        # ):
        #     return node
        if isinstance(node.value, (bool, type(None))) and str(node.value) in self.builtin_map:
            return ast.Name(id=self.builtin_map[str(node.value)], ctx=ast.Load())
        return node
