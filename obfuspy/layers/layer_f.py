import ast
import random
import string


class Layer_F(ast.NodeTransformer):
    """
    Layer F adds anti-debugging code to the AST.
    """
    def __init__(self, randomizer, __, probability: float) -> None:
        self.randomizer = randomizer
        self.probability = probability
        self.exec_alias_name = next(self.randomizer.random_name_gen)
        while self.exec_alias_name == 'exec':
            self.exec_alias_name = next(self.randomizer.random_name_gen)

    def anti_debug_code(self) -> ast.stmt:
        offset = random.randint(2, 6)
        anti_debug_stmt = 'import sys;sys.exit(0) if sys.gettrace() is not None else None'
        anti_debug_stmt = ''.join(c + ''.join(random.choice(string.ascii_letters) for _ in range(offset-1)) for c in anti_debug_stmt)
        return ast.parse(f"{self.exec_alias_name}('{anti_debug_stmt}'[::{offset}])").body

    def exec_alias_code(self) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=self.exec_alias_name, ctx=ast.Store())],
            value=ast.Name(id='exec', ctx=ast.Load()),
            lineno=0,
            col_offset=0,
        )

    @staticmethod
    def _module_insert_position(body: list) -> int:
        insert_position = 0
        if (
            body and
            isinstance(body[0], ast.Expr) and
            isinstance(body[0].value, ast.Constant) and
            isinstance(body[0].value.value, str)
        ):
            insert_position = 1

        for i in range(insert_position, len(body)):
            if not isinstance(body[i], (ast.Import, ast.ImportFrom)):
                return i
        return len(body)

    @staticmethod
    def _insert_start_for_docstring(body: list) -> int:
        if (
            body and
            isinstance(body[0], ast.Expr) and
            isinstance(body[0].value, ast.Constant) and
            isinstance(body[0].value.value, str)
        ):
            return 1
        return 0

    def insert_anti_debug_code(self, body: list, include_anchor: bool = False, min_insert_index: int = 0) -> None:
        if not body:
            return
        insert_start = max(self._insert_start_for_docstring(body), min_insert_index)

        if include_anchor:
            body[insert_start:insert_start] = self.anti_debug_code()
            insert_start += 1

        positions = range(insert_start, len(body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            body[i:i] = self.anti_debug_code()

    def visit_Module(self, node):
        alias_index = self._module_insert_position(node.body)
        node.body.insert(alias_index, self.exec_alias_code())
        self.insert_anti_debug_code(node.body, include_anchor=True, min_insert_index=alias_index + 1)
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
