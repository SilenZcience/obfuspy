import ast
from obfuspy.util.randomizer import Randomizer, ALL_BUILTINS


class ObfBuiltins(ast.NodeTransformer):
    """
    Obfuscates builtins.
    """
    def __init__(self, randomizer: Randomizer, _) -> None:
        self.randomizer = randomizer
        self.project_context = getattr(randomizer, 'project_context', {})
        defined_names = set(self.project_context.get('defined_names', set()))
        self.builtin_map = {
            b: next(self.randomizer.random_name_gen)
            for b in ALL_BUILTINS
            if b not in defined_names
        }

    def builtin_code(self):
        value = ','.join(map(str, self.builtin_map.values()))
        value += '='
        value += ','.join(map(str, self.builtin_map.keys()))
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id='exec', ctx=ast.Load()),
                args=[ast.Constant(value=value)],
                keywords=[]
            )
        )

    def visit_Module(self, node):
        if not self.builtin_map:
            return self.generic_visit(node)

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
        if node.id in self.builtin_map:
            return ast.Name(
                id=self.builtin_map[node.id],
                ctx=node.ctx
            )
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, (bool, type(None))) and str(node.value) in self.builtin_map:
            return ast.Name(id=self.builtin_map[str(node.value)], ctx=ast.Load())
        return node
