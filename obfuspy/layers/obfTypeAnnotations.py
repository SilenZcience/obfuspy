import ast
import random


class ObfTypeAnnotations(ast.NodeTransformer):
    """
    Obfuscates type annotations in function definitions and assignments.
    """
    def __init__(self, _, __) -> None:
        pass

    def random_annotation(self) -> list:
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

    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            arg.annotation = self.random_annotation()
        node.returns = self.random_annotation()
        return node

    def visit_AsyncFunctionDef(self, node):
        for arg in node.args.args:
            arg.annotation = self.random_annotation()
        node.returns = self.random_annotation()
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            ann_node = ast.AnnAssign(
                target=node.targets[0],
                annotation=self.random_annotation(),
                value=node.value,
                simple=1
            )
            ann_node.lineno = getattr(node, 'lineno', 1)
            ann_node.col_offset = getattr(node, 'col_offset', 0)
            return ann_node
        return node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        node.annotation = self.random_annotation()
        return node
