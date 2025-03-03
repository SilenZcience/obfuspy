import ast
import random
import string


class Layer_F(ast.NodeTransformer):
    """
    Layer F adds anti-debugging code to the AST.
    """
    def __init__(self, _, probability: float) -> None:
        self.probability = probability

    def anti_debug_code(self) -> ast.stmt:
        offset = random.randint(2, 6)
        anti_debug_stmt = 'import sys;sys.exit(0) if sys.gettrace() is not None else None'
        anti_debug_stmt = ''.join(c + ''.join(random.choice(string.ascii_letters) for _ in range(offset-1)) for c in anti_debug_stmt)
        return ast.parse(f"exec('{anti_debug_stmt}'[::{offset}])").body

    def insert_anti_debug_code(self, body: list) -> None:
        if not body:
            return
        # body[0:0] = self.anti_debug_code()
        positions = range(len(body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            body[i:i] = self.anti_debug_code()

    def visit_Module(self, node):
        node.body[0:0] = self.anti_debug_code()
        positions = range(1, len(node.body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            node.body[i:i] = self.anti_debug_code()
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.insert_anti_debug_code(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self.insert_anti_debug_code(node.body)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.insert_anti_debug_code(node.body)
        self.generic_visit(node)
        return node
