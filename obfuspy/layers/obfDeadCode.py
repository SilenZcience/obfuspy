import ast
import random
from obfuspy.util.randomizer import Randomizer


class ObfDeadCode(ast.NodeTransformer):
    """
    Inserts dead code.
    """
    def __init__(self, randomizer: Randomizer, _, probability: float) -> None:
        self.randomizer = randomizer
        self.probability = probability

    def dead_classes(self) -> ast.stmt:
        choices = [
            # Unused class with random methods
            lambda: ast.ClassDef(
                name=next(self.randomizer.random_name_gen),
                bases=[],
                keywords=[],
                body=[self.dead_functions() for _ in range(random.randint(1, 3))],
                decorator_list=[],
                lineno=0,
                col_offset=0
            ),
        ]
        return random.choice(choices)()

    def dead_functions(self) -> ast.stmt:
        random_args = [next(self.randomizer.random_name_gen) for _ in range(random.randint(1, 4))]
        choices = [
            # Unused function with random operations
            lambda: ast.FunctionDef(
                name=next(self.randomizer.random_name_gen),
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg=random_arg) for random_arg in random_args],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[self.dead_expressions() for _ in range(random.randint(1, 4))] + [
                    ast.Return(value=ast.Name(id=random.choice(random_args), ctx=ast.Load()))
                ],
                decorator_list=[],
                lineno=0,
                col_offset=0
            ),
        ]
        return random.choice(choices)()
# TODO: do not insert as much into loops
    def dead_expressions(self) -> ast.stmt: # TODO: more, loops etc, better integrated logic
        choices = [
            # Unused variable assignment with number
            lambda: ast.Assign(
                targets=[ast.Name(id=next(self.randomizer.random_name_gen), ctx=ast.Store())],
                value=ast.parse(str(random.randint(1, 9_999_999)), mode='eval').body,
                lineno=0,
                col_offset=0
            ),
            # Unused variable assignment with string
            lambda: ast.Assign(
                targets=[ast.Name(id=next(self.randomizer.random_name_gen), ctx=ast.Store())],
                value=ast.Constant(value=''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5, 15)))),
                lineno=0,
                col_offset=0
            ),
            # Unused variable assignment with list
            lambda: ast.Assign(
                targets=[ast.Name(id=next(self.randomizer.random_name_gen), ctx=ast.Store())],
                value=ast.List(
                    elts=[ast.Constant(value=random.randint(1, 100)) for _ in range(random.randint(2, 5))],
                    ctx=ast.Load()
                ),
                lineno=0,
                col_offset=0
            ),
        ]
        return random.choice(choices)()

    def dead_code(self) -> ast.stmt:
        return random.choice([
            self.dead_classes(),
            self.dead_functions(),
            self.dead_expressions(),
        ])

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

    def visit_Module(self, node):
        insert_start = self._insert_start_for_docstring(node.body)
        positions = range(insert_start, len(node.body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            node.body.insert(i, self.dead_code())
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        insert_start = self._insert_start_for_docstring(node.body)
        positions = range(insert_start, len(node.body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            node.body.insert(i, self.dead_functions())
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        insert_start = self._insert_start_for_docstring(node.body)
        positions = range(insert_start, len(node.body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            node.body.insert(i, self.dead_expressions())
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        insert_start = self._insert_start_for_docstring(node.body)
        positions = range(insert_start, len(node.body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            node.body.insert(i, self.dead_expressions())
        self.generic_visit(node)
        return node
