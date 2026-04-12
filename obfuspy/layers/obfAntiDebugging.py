import ast
import random
import string


ANTI_DEBUG_EXEC = [ # TODO: more variety
#     """import sys
# if sys.gettrace() is not None: sys.exit(0)
# """,
    """
if __import__('sys').gettrace() is not None:
    {0} = globals()['__builtins__']
    if isinstance({0},dict): {0}.clear()
    else: {0}.__dict__.clear()
""",
#     """import inspect
# for frame in inspect.stack():
#     frame_filename = frame.filename.lower()
#     for keyword in {"pdb","bdb","ipdb","pudb","rpdb","wdb","pydevd","debugpy","ptvsd"}:
#         if keyword in frame_filename: raise SystemExit(0)
# """,
    """
for {0} in __import__('inspect').stack():
    {1} = {0}.filename.lower()
    for {2} in {{"pdb","bdb","ipdb","pudb","rpdb","wdb","pydevd","debugpy","ptvsd"}}:
        if {2} in {1}:
            {3} = globals()['__builtins__']
            if isinstance({3},dict): {3}.clear()
            else: {3}.__dict__.clear()
            break
""",
#     """import sys
# for name in sys.modules:
#     module_name = name.lower()
#     for dbg in {"pdb","bdb","ipdb","pudb","rpdb","wdb","pydevd","debugpy","ptvsd"}:
#         if dbg in module_name: sys.exit(0)
# """,
    """
for {0} in __import__('sys').modules:
    {1} = {0}.lower()
    for {2} in {{"pdb","bdb","ipdb","pudb","rpdb","wdb","pydevd","debugpy","ptvsd"}}:
        if {2} in {1}:
            {3} = globals()['__builtins__']
            if isinstance({3},dict): {3}.clear()
            else: {3}.__dict__.clear()
            break
""",
] # beware that iterative variables make problems inside class bodies
ANTI_DEBUG_LAMBDA = [ # TODO: use generated variable names!
    """__import__('sys').gettrace() is not None and (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'],dict) else globals()['__builtins__'].__dict__.clear())""",
    """any(frame.filename.lower().find(keyword)!=-1 for frame in __import__('inspect').stack() for keyword in {'pdb','bdb','ipdb','pudb','rpdb','wdb','pydevd','debugpy','ptvsd'}) and (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'],dict) else globals()['__builtins__'].__dict__.clear())""",
    """any(name.lower().find(dbg)!=-1 for name in __import__('sys').modules for dbg in {'pdb','bdb','ipdb','pudb','rpdb','wdb','pydevd','debugpy','ptvsd'}) and (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'],dict) else globals()['__builtins__'].__dict__.clear())""",
]


class ObfAntiDebugging(ast.NodeTransformer):
    """
    Adds anti-debugging code.
    """
    def __init__(self, randomizer, __, probability: float) -> None:
        self.randomizer = randomizer
        self.probability = probability
        self.exec_alias_name = next(self.randomizer.random_name_gen)
        while self.exec_alias_name == 'exec':
            self.exec_alias_name = next(self.randomizer.random_name_gen)

    def anti_debug_code(self) -> ast.stmt:
        if random.random() < 1.5:
            return ast.parse(random.choice(ANTI_DEBUG_EXEC).format(
                next(self.randomizer.random_name_gen),
                next(self.randomizer.random_name_gen),
                next(self.randomizer.random_name_gen),
                next(self.randomizer.random_name_gen),
            )).body

        if random.random() < 0.5:
            offset = random.randint(2, 6)
            anti_debug_stmt = random.choice(ANTI_DEBUG_EXEC).format(
                next(self.randomizer.random_name_gen),
                next(self.randomizer.random_name_gen),
                next(self.randomizer.random_name_gen),
                next(self.randomizer.random_name_gen),
            )
            anti_debug_stmt = ''.join(c + ''.join(random.choice(string.ascii_letters) for _ in range(offset-1)) for c in anti_debug_stmt)
            return ast.parse(f"{self.exec_alias_name}({anti_debug_stmt!r}[::{offset}])").body

        anti_debug_stmt = random.choice(ANTI_DEBUG_LAMBDA)
        return ast.parse(
            f"(lambda: {anti_debug_stmt})()"
        ).body

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
