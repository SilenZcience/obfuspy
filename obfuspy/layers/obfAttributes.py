import ast


class ObfAttributes(ast.NodeTransformer):
    """
    Obfuscates attributes by replacing them with getattr() and setattr() calls.
    """

    def __init__(self, _, __) -> None:
        pass

    def visit_Assign(self, node):
        node = self.generic_visit(node)
        new_nodes = []
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                new_node = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="setattr", ctx=ast.Load()),
                        args=[
                            target.value,
                            ast.Constant(target.attr),
                            node.value,
                        ],
                        keywords=[],
                    )
                )
                new_nodes.append(ast.copy_location(new_node, node))
            else:
                new_node = ast.Assign(targets=[target], value=node.value)
                new_nodes.append(ast.copy_location(new_node, node))
        return new_nodes

    def visit_AnnAssign(self, node):
        node = self.generic_visit(node)
        if isinstance(node.target, ast.Attribute):
            new_node = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="setattr", ctx=ast.Load()),
                    args=[
                        node.target.value,
                        ast.Constant(node.target.attr),
                        node.value,
                    ],
                    keywords=[],
                )
            )
            return ast.copy_location(new_node, node)
        else:
            return node

    def visit_AugAssign(self, node):
        node = self.generic_visit(node)
        if isinstance(node.target, ast.Attribute):
            new_node = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="setattr", ctx=ast.Load()),
                    args=[
                        node.target.value,
                        ast.Constant(node.target.attr),
                        ast.BinOp(
                            left=ast.Call(
                                func=ast.Name(id="getattr", ctx=ast.Load()),
                                args=[
                                    node.target.value,
                                    ast.Constant(node.target.attr),
                                ],
                                keywords=[],
                            ),
                            op=node.op,
                            right=node.value,
                        ),
                    ],
                    keywords=[],
                )
            )
            return ast.copy_location(new_node, node)
        else:
            return node

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if isinstance(node.ctx, ast.Load):
            new_node = ast.Call(
                func=ast.Name(id="getattr", ctx=ast.Load()),
                args=[
                    node.value,
                    ast.Constant(node.attr),
                ],
                keywords=[],
            )
            return ast.copy_location(new_node, node)

        return node
