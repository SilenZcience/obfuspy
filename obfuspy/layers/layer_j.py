import ast
from obfuspy.util.randomizer import Randomizer


class Layer_J(ast.NodeTransformer):
    """
    Layer J obfuscates function/method arguments in the AST.
    """
    def __init__(self, randomizer: Randomizer) -> None:
        self.randomizer = randomizer
        self.arg_map = {}

    def visit_FunctionDef(self, node):
        arg_map = {}
        current_arg_map = self.arg_map.copy()
        for arg in node.args.args:
            arg_map[arg.arg] = next(self.randomizer.random_name_gen)
            arg.arg = arg_map[arg.arg]
        self.arg_map |= arg_map
        self.generic_visit(node)
        self.arg_map = current_arg_map
        return node

    def visit_AsyncFunctionDef(self, node):
        arg_map = {}
        current_arg_map = self.arg_map.copy()
        for arg in node.args.args:
            arg_map[arg.arg] = next(self.randomizer.random_name_gen)
            arg.arg = arg_map[arg.arg]
        self.arg_map |= arg_map
        self.generic_visit(node)
        self.arg_map = current_arg_map
        return node

    def visit_Name(self, node):
        print(node.id)
        if node.id in self.arg_map:
            node.id = self.arg_map[node.id]
        return node
