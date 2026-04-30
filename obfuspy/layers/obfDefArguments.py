import ast
import random

from obfuspy.util.domain import SYMBOL_MAP, Node
from obfuspy.util.randomizer import Randomizer


class ObfDefArguments(ast.NodeTransformer):
    """
    Obfuscates function/method arguments.
    """
    def __init__(self, randomizer: Randomizer, file_module):
        self.randomizer = randomizer
        self.module_name = getattr(file_module, 'module_name', None)
        self.prefix_parts = []
        self._defarg_name_map_stack = []  # Stack of dicts: {original_arg_name: obf_value}
        self._defarg_name_map_cache = {}

    def _push_defarg_name_scope(self):
        key = tuple((lbl.ltype, lbl.name) for lbl in self.prefix_parts)
        if key in self._defarg_name_map_cache:
            defarg_name_map = self._defarg_name_map_cache[key]
        else:
            defarg_name_map = SYMBOL_MAP.get_defargs(self.prefix_parts)
            self._defarg_name_map_cache[key] = defarg_name_map
        self._defarg_name_map_stack.append(defarg_name_map)

    def _pop_defarg_name_scope(self):
        if self._defarg_name_map_stack:
            self._defarg_name_map_stack.pop()

    def _current_defarg_name_map(self):
        return self._defarg_name_map_stack[-1] if self._defarg_name_map_stack else {}

    def _visit_callable(self, node):
        if isinstance(node, ast.Lambda):
            defarg_name_map = {}
            for arg in getattr(node.args, 'posonlyargs', []):
                if arg:
                    defarg_name_map[arg.arg] = {
                        'name': next(self.randomizer.random_name_gen),
                    }
            for arg in getattr(node.args, 'args', []):
                if arg:
                    defarg_name_map[arg.arg] = {
                        'name': next(self.randomizer.random_name_gen),
                    }
            for arg in getattr(node.args, 'kwonlyargs', []):
                if arg:
                    defarg_name_map[arg.arg] = {
                        'name': next(self.randomizer.random_name_gen),
                    }
            if getattr(node.args, 'vararg', None):
                defarg_name_map[node.args.vararg.arg] = {
                    'name': next(self.randomizer.random_name_gen),
                }
            if getattr(node.args, 'kwarg', None):
                defarg_name_map[node.args.kwarg.arg] = {
                    'name': next(self.randomizer.random_name_gen),
                }
            self._defarg_name_map_stack.append(defarg_name_map)
        else:
            self.prefix_parts.append(Node.Def(node.name))
            self._push_defarg_name_scope()
            defarg_name_map = self._current_defarg_name_map()

        for arg in getattr(node.args, 'posonlyargs', []):
            if arg and arg.arg in defarg_name_map:
                arg.arg = defarg_name_map[arg.arg]['name']
        for arg in getattr(node.args, 'args', []):
            if arg and arg.arg in defarg_name_map:
                arg.arg = defarg_name_map[arg.arg]['name']
        for arg in getattr(node.args, 'kwonlyargs', []):
            if arg and arg.arg in defarg_name_map:
                arg.arg = defarg_name_map[arg.arg]['name']
        if getattr(node.args, 'vararg', None) and node.args.vararg.arg in defarg_name_map:
            node.args.vararg.arg = defarg_name_map[node.args.vararg.arg]['name']
        if getattr(node.args, 'kwarg', None) and node.args.kwarg.arg in defarg_name_map:
            node.args.kwarg.arg = defarg_name_map[node.args.kwarg.arg]['name']

        r_vars = [next(SYMBOL_MAP.randomizer.random_name_gen) for _ in range(random.randint(1, 5))]

        if not getattr(node.args, 'kwarg', None) and getattr(node.args, 'kwonlyargs', []):
            for r_var in r_vars:
                node.args.kwonlyargs.append(ast.arg(arg=r_var, annotation=None))
                node.args.kw_defaults.append(ast.Constant(value=random.choice([None, True, False])))
        elif not getattr(node.args, 'kwarg', None) and not getattr(node.args, 'vararg', None):
            for r_var in r_vars:
                node.args.args.append(ast.arg(arg=r_var, annotation=None))
                node.args.defaults.append(ast.Constant(value=random.choice([None, True, False])))
        else:
            r_vars.clear()

        if isinstance(node, ast.Lambda):
            self.visit(node.body)
            self._pop_defarg_name_scope()
        else:
            for stmt in node.body:
                self.visit(stmt)
            for r_var in r_vars:
                r_pos = random.randint(0, len(node.body)-1)
                node.body[r_pos:r_pos] = [ast.Assign(
                    targets=[ast.Name(id=r_var, ctx=ast.Store())],
                    value=ast.Name(id=r_var, ctx=ast.Load()),
                    lineno=getattr(node.body[r_pos], 'lineno', 0),
                    col_offset=getattr(node.body[r_pos], 'col_offset', 0),
                )]

            self._pop_defarg_name_scope()
            self.prefix_parts.pop()

        return node

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self._defarg_name_map_stack = []
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.prefix_parts.append(Node.Cls(node.name))
        self.generic_visit(node)
        self.prefix_parts.pop()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_callable(node)

    def visit_Lambda(self, node):
        return self._visit_callable(node)

    def visit_Name(self, node):
        for scope in reversed(self._defarg_name_map_stack):
            if node.id in scope:
                node.id = scope[node.id]['name']
                break
        return node
