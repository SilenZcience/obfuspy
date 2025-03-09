import ast
from obfuspy.util.randomizer import Randomizer



class Layer_I(ast.NodeTransformer):
    """
    Layer I obfuscates imports in the AST.
    """
    def __init__(self, randomizer: Randomizer) -> None:
        self.randomizer = randomizer
        self.import_map = {}

    def visit_Module(self, node):
        self.import_map = {}
        self.generic_visit(node)
        return node

    def visit_Import(self, node):
        for name in node.names:
            if name.asname is not None:
                self.import_map[name.asname] = next(self.randomizer.random_name_gen)
                name.asname = self.import_map[name.asname]
            else:
                self.import_map[name.name] = next(self.randomizer.random_name_gen)
                name.asname = self.import_map[name.name]
        return node

    def visit_ImportFrom(self, node):
        for name in node.names:
            if name.name == '*':
                continue
            if name.asname is not None:
                self.import_map[name.asname] = next(self.randomizer.random_name_gen)
                name.asname = self.import_map[name.asname]
            else:
                self.import_map[name.name] = next(self.randomizer.random_name_gen)
                name.asname = self.import_map[name.name]
        return node

    def visit_Global(self, node):
        new_names = []
        for name in node.names:
            if name in self.import_map:
                new_names.append(self.import_map[name])
            else:
                new_names.append(name)
        node.names = new_names
        return node

    def visit_Nonlocal(self, node):
        new_names = []
        for name in node.names:
            if name in self.import_map:
                new_names.append(self.import_map[name])
            else:
                new_names.append(name)
        node.names = new_names
        return node

    def visit_Attribute(self, node):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            full_path = '.'.join(reversed(parts))
            if full_path in self.import_map:
                return ast.Name(
                    id=self.import_map[full_path],
                    ctx=node.ctx
                )

        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        if node.id in self.import_map:
            return ast.Name(
                id=self.import_map[node.id],
                ctx=node.ctx
            )
        return node
