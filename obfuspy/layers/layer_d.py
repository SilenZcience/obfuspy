import ast


class Layer_D(ast.NodeTransformer):
    """
    Layer D obfuscates assignments in the AST.
    """
    def __init__(self, _) -> None:
        pass

    def visit_Assign(self, node):
        # x = y = 2 -> y = 2; x = y
        if len(node.targets) > 1:
            result = []
            for target in reversed(node.targets):
                if isinstance(target, ast.Name):
                    assign = ast.Assign(
                        targets=[target],
                        value=node.value if target is node.targets[-1]
                            else ast.Name(id=node.targets[node.targets.index(target) + 1].id,
                                        ctx=ast.Load()),
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    )
                    result.append(self.visit(assign))
            return result
        # a, b = 1, 2 -> a = 1; b = 2
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple):
            if isinstance(node.value, ast.Tuple):
                result = []
                for target, value in zip(node.targets[0].elts, node.value.elts):
                    if isinstance(target, ast.Name):
                        result.append(ast.Assign(
                            targets=[target],
                            value=value,
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        ))
                return result

        self.generic_visit(node)
        return node

    def visit_AugAssign(self, node):
        # x += 1 -> x = x + 1
        self.generic_visit(node)
        if isinstance(node.target, ast.Name):
            return ast.Assign(
                targets=[node.target],
                value=ast.BinOp(
                    left=ast.Name(id=node.target.id, ctx=ast.Load()),
                    op=node.op,
                    right=node.value
                ),
                lineno=node.lineno,
                col_offset=node.col_offset
            )
        return node

    def visit_AnnAssign(self, node):
        # x: int = 1 -> x = 1
        self.generic_visit(node)
        return ast.Assign(
            targets=[node.target],
            value=node.value,
            lineno=node.lineno,
            col_offset=node.col_offset
        )
