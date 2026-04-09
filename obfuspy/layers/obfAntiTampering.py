import ast
import hashlib
import random
import inspect
from functools import lru_cache

AST_NODE_TYPES = {
    obj for _, obj in inspect.getmembers(ast)
    if inspect.isclass(obj) and issubclass(obj, ast.AST)
}

# verify:
# with open(__file__, 'r', encoding='utf-8') as f:
#     print((lambda tree:(lambda h:(list(map(lambda node:isinstance(node, ast.Add)and (print(ast.dump(node).encode()),h.update(ast.dump(node).encode())),ast.walk(tree))),h.hexdigest())[1])(hashlib.sha256()))(ast.parse(f.read())))
# # (_ for _ in ()).throw(SystemExit(55))

ANTI_TAMPERING_EXEC = """import ast, hashlib
source = open(__file__, 'r', encoding='utf-8').read()
tree = ast.parse(source)
h = hashlib.sha256()
for node in ast.walk(tree):
    if isinstance(node, ast.REPLACEMETYPE):
        h.update(ast.dump(node).encode())
if h.hexdigest() != 'REPLACEMEHASH':
    (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'], dict) else globals()['__builtins__'].__dict__.clear())
"""
ANTI_TEMPERING_EXEC_NODES = set()
for node in ast.walk(ast.parse(ANTI_TAMPERING_EXEC)):
    ANTI_TEMPERING_EXEC_NODES.add(type(node))

ANTI_TEMPERING_LAMBDA = """(
    lambda ast,hashlib:
    (
        lambda tree,h:
        (
            [(h.update(ast.dump(node).encode())) for node in ast.walk(tree) if isinstance(node,ast.REPLACEMETYPE)], h.hexdigest()
        )[1]
    )(ast.parse(open(__file__,'r',encoding='utf-8').read()), hashlib.sha256()) == 'REPLACEMEHASH' or (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'], dict) else globals()['__builtins__'].__dict__.clear())
)(__import__('ast'),__import__('hashlib'))"""
ANTI_TEMPERING_LAMBDA_NODES = set()
for node in ast.walk(ast.parse(ANTI_TEMPERING_LAMBDA)):
    ANTI_TEMPERING_LAMBDA_NODES.add(type(node))

AST_NODE_TYPES -= ANTI_TEMPERING_EXEC_NODES
AST_NODE_TYPES -= ANTI_TEMPERING_LAMBDA_NODES
AST_NODE_TYPES = {ast.If}

class ObfAntiTampering(ast.NodeTransformer):
    """
    Adds anti-tampering code.
    """
    def __init__(self, randomizer, _, probability: float) -> None:
        self.randomizer = randomizer
        self.probability = probability
        self.exec_alias_name = next(self.randomizer.random_name_gen)
        while self.exec_alias_name == 'exec':
            self.exec_alias_name = next(self.randomizer.random_name_gen)
        self.possible_types = list(AST_NODE_TYPES)
        self.module_node = None

    @lru_cache()
    def _node_tree_hash(self, node_type):
        node_hash = hashlib.sha256()
        for current_node in ast.walk(self.module_node):
            if isinstance(current_node, node_type):
                current_node.body = []
                print(ast.dump(current_node))
                node_hash.update(ast.dump(current_node).encode())
        return node_hash

    def anti_tampering_code(self) -> ast.stmt:
        node_type = random.choice(self.possible_types)
        node_hash = self._node_tree_hash(node_type)
        if random.random() < 2.0:
            anti_tampering_stmt = ANTI_TAMPERING_EXEC.replace('REPLACEMETYPE', node_type.__name__).replace('REPLACEMEHASH', node_hash.hexdigest())
            return ast.parse(f"{self.exec_alias_name}({anti_tampering_stmt!r})").body

        anti_tampering_stmt = ANTI_TEMPERING_LAMBDA.replace('REPLACEMETYPE', node_type.__name__).replace('REPLACEMEHASH', node_hash.hexdigest())
        return ast.parse(
            f"(lambda: {anti_tampering_stmt})()"
        ).body


    def exec_alias_code(self) -> ast.Assign:
        exec_alias = ast.Assign(
            targets=[ast.Name(id=self.exec_alias_name, ctx=ast.Store())],
            value=ast.Name(id='exec', ctx=ast.Load()),
            lineno=0,
            col_offset=0,
        )
        return exec_alias

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

    def insert_anti_tampering_code(self, body: list, include_anchor: bool = False, min_insert_index: int = 0) -> None:
        if not body:
            return
        insert_start = max(self._insert_start_for_docstring(body), min_insert_index)

        if include_anchor:
            body[insert_start:insert_start] = self.anti_tampering_code()
            insert_start += 1

        positions = range(insert_start, len(body) + 1)
        insert_count = int(len(positions) * self.probability)
        for i in sorted(random.sample(positions, insert_count), reverse=True):
            body[i:i] = self.anti_tampering_code()

    def visit_Module(self, node):
        self.module_node = node
        alias_index = self._module_insert_position(node.body)
        node.body.insert(alias_index, self.exec_alias_code())

        possible_types = set()
        for current_node in ast.walk(node):
            possible_types.add(type(current_node))
        self.possible_types = list(AST_NODE_TYPES & possible_types)

        if not self.possible_types:
            print("Warning: No suitable AST node types found for anti-tampering code. Consider reducing the obfuscation level or using a different layer combination.")
            return
            raise ValueError("No suitable AST node types found for anti-tampering code. Consider reducing the obfuscation level or using a different layer combination.")

        self.insert_anti_tampering_code(node.body, include_anchor=True, min_insert_index=alias_index + 1)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.insert_anti_tampering_code(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self.insert_anti_tampering_code(node.body)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.insert_anti_tampering_code(node.body)
        self.generic_visit(node)
        return node
