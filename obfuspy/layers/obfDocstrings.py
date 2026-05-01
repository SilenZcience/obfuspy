import ast
import random
from obfuspy.util.randomizer import Randomizer


class ObfDocStrings(ast.NodeTransformer): # TODO: maybe confusing text instead of gibberish
    """
    Obfuscates docstrings (__doc__).
    """

    def __init__(self, randomizer: Randomizer, _) -> None:
        self.randomizer = randomizer

    def visit_Module(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        self.generic_visit(node)
        node.body.insert(0, ast.Expr(
            value=ast.Constant(
                value='\n'.join([
                    next(self.randomizer.random_name_gen)
                    for _ in range(random.randint(3, 6))
                ])
            )
        ))
        return node

    def visit_ClassDef(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        self.generic_visit(node)
        node.body.insert(0, ast.Expr(
            value=ast.Constant(
                value='\n'.join([
                    next(self.randomizer.random_name_gen)
                    for _ in range(random.randint(3, 6))
                ])
            )
        ))
        return node

    def visit_FunctionDef(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        self.generic_visit(node)
        node.body.insert(0, ast.Expr(
            value=ast.Constant(
                value='\n'.join([
                    next(self.randomizer.random_name_gen)
                    for _ in range(random.randint(3, 6))
                ])
            )
        ))
        return node

    def visit_AsyncFunctionDef(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        self.generic_visit(node)
        node.body.insert(0, ast.Expr(
            value=ast.Constant(
                value='\n'.join([
                    next(self.randomizer.random_name_gen)
                    for _ in range(random.randint(3, 6))
                ])
            )
        ))
        return node
