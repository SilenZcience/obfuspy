import ast


class ObfAssignements(ast.NodeTransformer):
    """
    Obfuscates simple assignments by splitting tuple-assignements and chained assignements into multiple lines.
    """

    def __init__(self, _, __) -> None:
        pass

    def _to_load_expr(self, target):
        if isinstance(target, ast.Name):
            return ast.Name(id=target.id, ctx=ast.Load())
        if isinstance(target, ast.Attribute):
            return ast.Attribute(
                value=self._to_load_expr(target.value),
                attr=target.attr,
                ctx=ast.Load()
            )
        if isinstance(target, ast.Subscript):
            return ast.Subscript(
                value=self._to_load_expr(target.value),
                slice=target.slice,
                ctx=ast.Load()
            )
        return target

    def visit_Assign(self, node):
        # x = y = 2 -> y = 2; x = y
        if len(node.targets) > 1:
            result = []
            current_value = node.value
            for target in reversed(node.targets):
                assign = ast.Assign(
                    targets=[target],
                    value=current_value,
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
                result.append(self.visit(assign))
                current_value = self._to_load_expr(target)
            return result
        # a, b = 1, 2 -> a = 1; b = 2
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple):
            if isinstance(node.value, ast.Tuple):
                result = []
                for target, value in zip(node.targets[0].elts, node.value.elts):
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
        if isinstance(node.target, (ast.Name, ast.Attribute, ast.Subscript)):
            return ast.Assign(
                targets=[node.target],
                value=ast.BinOp(
                    left=self._to_load_expr(node.target),
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
