import ast
import functools
import random
from obfuspy.util.randomizer import Randomizer


# def generate_builtin_code(var_map: dict) -> list:
#     return ast.Assign(
#         targets=[ast.Tuple(
#             elts=[ast.Name(id=var_map[b], ctx=ast.Store()) for b in ALL_BUILTINS],
#             ctx=ast.Store()
#         )],
#         value=ast.Tuple(
#             elts=[ast.Name(id=b, ctx=ast.Load()) for b in ALL_BUILTINS],
#             ctx=ast.Load()
#         ),
#         lineno=0,
#         col_offset=0
#     )


class Visitor_A(ast.NodeTransformer):
    def __init__(self, randomizer: Randomizer) -> None:
        self.randomizer = randomizer

    def visit_Module(self, node):
        self.generic_visit(node)
        # if OBFUSCATE_BUILTINS:
        #     node.body.insert(insert_position, generate_builtin_code(self.var_map))
        return node

    # def visit_Import(self, node):
    #     for name in node.names:
    #         if name.asname:
    #             if name.asname in self.var_map:
    #                 name.asname = self.var_map[name.asname]
    #     return node

    # def visit_ImportFrom(self, node):
    #     for name in node.names:
    #         if name.asname:
    #             if name.asname in self.var_map:
    #                 name.asname = self.var_map[name.asname]
    #     if node.module.split('.')[-1] not in self.file_map:
    #         return node
    #     for name in node.names:
    #         if name.name in self.var_map:
    #             name.name = self.var_map[name.name]
    #     return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        return node

    # def visit_Global(self, node):
    #     new_names = []
    #     for name in node.names:
    #         if name in self.var_map:
    #             new_names.append(self.var_map[name])
    #         else:
    #             new_names.append(name)
    #     node.names = new_names
    #     return node

    # def visit_Nonlocal(self, node):
    #     new_names = []
    #     for name in node.names:
    #         if name in self.var_map:
    #             new_names.append(self.var_map[name])
    #         else:
    #             new_names.append(name)
    #     node.names = new_names
    #     return node

    # def visit_Attribute(self, node):
    #     self.generic_visit(node)
        # current = node
        # root = None
        # while isinstance(current, ast.Attribute):
        #     current = current.value
        #     if isinstance(current, ast.Name):
        #         root = current
        #         break

        # if root and root.id in self.file_map:
        #     root.id = self.file_map[root.id]
        # if node.attr in self.var_map:
        #     node.attr = self.var_map[node.attr]

        # return node

    # def visit_Name(self, node):
    #     if node.id in self.skip_names:
    #         return node

    #     if node.id in self.var_map:
    #         node.id = self.var_map[node.id]
    #     return node

    # def visit_arg(self, node):
    #     if node.arg in self.var_map:
    #         node.arg = self.var_map[node.arg]
    #     return node

    def visit_Constant(self, node):
        if isinstance(node.value, (bool, type(None))):
            return node
        # if OBFUSCATE_BUILTINS and isinstance(node.value, (bool, type(None))):
            # return ast.Name(id=self.var_map[str(node.value)], ctx=ast.Load())
