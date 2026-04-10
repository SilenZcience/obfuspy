import ast
import hashlib
import random
from functools import lru_cache

AST_NODE_TYPES = {
    # ast.Assign,
    # ast.AnnAssign,
    # ast.AugAssign,

    # ast.Import,
    ast.ImportFrom,

    # ast.Yield,
    # ast.YieldFrom,
    ast.Return,

    ast.Try,
    ast.ExceptHandler,
    ast.While,
    # ast.For,
    # ast.If,
    ast.Continue,
    ast.Break,
    ast.Pass,

    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef, # TODO: gets fucked by dead code
}# TODO: this is too weak

# exit(0)
# verify:
# with open(__file__, 'r', encoding='utf-8') as f:
#     print((lambda tree:(lambda h:(list(map(lambda node:isinstance(node, ast.Add)and (print(ast.dump(node).encode()),h.update(ast.dump(node).encode())),ast.walk(tree))),h.hexdigest())[1])(hashlib.sha256()))(ast.parse(f.read())))
# # (_ for _ in ()).throw(SystemExit(55))
# # (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'], dict) else globals()['__builtins__'].__dict__.clear())

ANTI_TAMPERING_EXEC = """import ast, hashlib
source = __import__('builtins').open(__file__, 'r', encoding='utf-8').read()
tree = ast.parse(source)
h = hashlib.sha256()
hattr = __import__('builtins').hasattr
for node in ast.walk(tree):
    if isinstance(node, ast.REPLACEMETYPE):
        if hattr(node, 'body'):
            node.body = []
        h.update(ast.dump(node).encode())
if h.hexdigest() != 'REPLACEMEHASH':
    (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'], dict) else globals()['__builtins__'].__dict__.clear())
"""
# ANTI_TEMPERING_EXEC_NODES = set()
# for node in ast.walk(ast.parse(ANTI_TAMPERING_EXEC)):
#     ANTI_TEMPERING_EXEC_NODES.add(type(node))

ANTI_TEMPERING_LAMBDA = """(
    lambda ast,hashlib,builtins:
    (
        lambda tree,h:
        (
            [
                (builtins.hasattr(node, 'body') and builtins.setattr(node,'body',[]), h.update(ast.dump(node).encode()))
                for node in ast.walk(tree)
                if isinstance(node,ast.REPLACEMETYPE)
            ],
            h.hexdigest()
        )[1]
    )(ast.parse(builtins.open(__file__,'r',encoding='utf-8').read()), hashlib.sha256()) == 'REPLACEMEHASH' or (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'], dict) else globals()['__builtins__'].__dict__.clear())
)(__import__('ast'),__import__('hashlib'),__import__('builtins'))"""
# ANTI_TEMPERING_LAMBDA_NODES = set()
# for node in ast.walk(ast.parse(ANTI_TEMPERING_LAMBDA)):
#     ANTI_TEMPERING_LAMBDA_NODES.add(type(node))
with open(__file__, 'r') as f:
    f.read().splitlines

class ObfAntiTampering(ast.NodeTransformer):
    """
    Adds anti-tampering code.
    """
    HASH_NODES = {}
    HASH_ID = 0

    def __init__(self, randomizer, file_module, probability: float) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        ObfAntiTampering.HASH_NODES[file_module] = {}
        self.probability = probability
        self.exec_alias_name = next(self.randomizer.random_name_gen)
        while self.exec_alias_name == 'exec':
            self.exec_alias_name = next(self.randomizer.random_name_gen)
        self.possible_types = list(AST_NODE_TYPES)

    # @lru_cache()
    # def _node_tree_hash(self, node_type):
    #     node_hash = hashlib.sha256()
    #     for current_node in ast.walk(self.module_node):
    #         if isinstance(current_node, node_type):
    #             if hasattr(current_node, 'body'):
    #                 current_node_body = current_node.body
    #                 current_node.body = []
    #                 node_hash.update(ast.dump(current_node).encode())
    #                 current_node.body = current_node_body
    #             else:
    #                 node_hash.update(ast.dump(current_node).encode())
    #     return node_hash

    def anti_tampering_code(self, node_type = None) -> ast.stmt:
        ObfAntiTampering.HASH_ID += 1
        tmp_var = next(self.randomizer.random_name_gen)
        anti_tampering_stmt = ast.parse(f"""{tmp_var} = ';;REPLACEMEHASH'
if sum(i * ord(c) for i, c in enumerate(''.join(__import__('builtins').open(__file__, 'r', encoding='utf-8').read().splitlines()[int({tmp_var}.split(';')[0]) : int({tmp_var}.split(';')[1])]), start=1)) % (2**64) != int({tmp_var}.split(';')[2]):
    (globals()['__builtins__'].clear() if isinstance(globals()['__builtins__'], dict) else globals()['__builtins__'].__dict__.clear())
""").body
        for node in anti_tampering_stmt:
            for s_node in ast.walk(node):
                if isinstance(s_node, ast.Constant) and isinstance(s_node.value, str) and s_node.value == ';;REPLACEMEHASH':
                    ObfAntiTampering.HASH_NODES[self.file_module][s_node] = []
        return anti_tampering_stmt
        # node_type = random.choice(self.possible_types) if node_type is None else node_type
        # node_hash = self._node_tree_hash(node_type)
        # if random.random() < 0.5:
        #     anti_tampering_stmt = ANTI_TAMPERING_EXEC.replace('REPLACEMETYPE', node_type.__name__).replace('REPLACEMEHASH', node_hash.hexdigest())
        #     return ast.parse(anti_tampering_stmt).body

        # if random.random() < 0.5:
        #     anti_tampering_stmt = ANTI_TAMPERING_EXEC.replace('REPLACEMETYPE', node_type.__name__).replace('REPLACEMEHASH', node_hash.hexdigest())
        #     return ast.parse(f"{self.exec_alias_name}({anti_tampering_stmt!r})").body

        # anti_tampering_stmt = ANTI_TEMPERING_LAMBDA.replace('REPLACEMETYPE', node_type.__name__).replace('REPLACEMEHASH', node_hash.hexdigest())
        # return ast.parse(
        #     f"(lambda: {anti_tampering_stmt})()"
        # ).body


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
        alias_index = self._module_insert_position(node.body)
        node.body.insert(alias_index, self.exec_alias_code())

        # possible_types = set()
        # for current_node in ast.walk(node):
        #     possible_types.add(type(current_node))
        # possible_types = AST_NODE_TYPES & possible_types
        # if len(AST_NODE_TYPES) > len(possible_types):
        #     possible_types |= set(random.choices(list(AST_NODE_TYPES - possible_types), k=min(len(AST_NODE_TYPES) - len(possible_types), 5)))
        # self.possible_types = list(possible_types)

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

    @staticmethod
    def finalize_hash_nodes(out_code: str, file_module):
        o_code = out_code.splitlines()
        # print(o_code)
        indexes = [i for i, line in enumerate(o_code) if ';;REPLACEMEHASH' in line]
        slices = []
        prev = 0
        for i in indexes:
            slices.append((prev, i))
            prev = i + 1
        slices.append((prev, len(o_code)))

        hash_nodes = ObfAntiTampering.HASH_NODES.get(file_module, {})
        for node in hash_nodes.keys():
            slice = random.choice(slices)
            node.value = f"{slice[0]};{slice[1]};{sum(i * ord(c) for i, c in enumerate(''.join(o_code[slice[0]:slice[1]]), start=1)) % (2**64)}"

        for i, (node, layers) in enumerate(hash_nodes.items(), start=1):
            for layer in layers:
                node = layer.visit(node)
            o_code[indexes[i-1]] = o_code[indexes[i-1]].replace("';;REPLACEMEHASH'", ast.unparse(node))
        return '\n'.join(o_code)
