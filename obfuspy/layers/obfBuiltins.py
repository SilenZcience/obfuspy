import ast

from obfuspy.util.randomizer import Randomizer, ALL_BUILTINS


def _collect_defined_names(file_module) -> set:
    defined = set()

    class DefinedNameCollector(ast.NodeVisitor):
        @staticmethod
        def _add_arg_names(args_node) -> None:
            for arg in getattr(args_node, 'posonlyargs', []):
                defined.add(arg.arg)
            for arg in getattr(args_node, 'args', []):
                defined.add(arg.arg)
            for arg in getattr(args_node, 'kwonlyargs', []):
                defined.add(arg.arg)
            vararg = getattr(args_node, 'vararg', None)
            if vararg is not None:
                defined.add(vararg.arg)
            kwarg = getattr(args_node, 'kwarg', None)
            if kwarg is not None:
                defined.add(kwarg.arg)

        @staticmethod
        def _add_target_names(target) -> None:
            if isinstance(target, ast.Name):
                defined.add(target.id)
                return
            if isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    DefinedNameCollector._add_target_names(element)
                return
            if isinstance(target, ast.Starred):
                DefinedNameCollector._add_target_names(target.value)

        def visit_FunctionDef(self, node):
            defined.add(node.name)
            self._add_arg_names(node.args)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            defined.add(node.name)
            self._add_arg_names(node.args)
            self.generic_visit(node)

        def visit_Lambda(self, node):
            self._add_arg_names(node.args)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            defined.add(node.name)
            self.generic_visit(node)

        def visit_Assign(self, node):
            for target in node.targets:
                self._add_target_names(target)
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            self._add_target_names(node.target)
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            self._add_target_names(node.target)
            self.generic_visit(node)

        def visit_For(self, node):
            self._add_target_names(node.target)
            self.generic_visit(node)

        def visit_AsyncFor(self, node):
            self._add_target_names(node.target)
            self.generic_visit(node)

        def visit_With(self, node):
            for item in node.items:
                if item.optional_vars is not None:
                    self._add_target_names(item.optional_vars)
            self.generic_visit(node)

        def visit_AsyncWith(self, node):
            for item in node.items:
                if item.optional_vars is not None:
                    self._add_target_names(item.optional_vars)
            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            if isinstance(node.name, str):
                defined.add(node.name)
            self.generic_visit(node)

        def visit_Import(self, node):
            for name in node.names:
                defined.add(name.asname or name.name.split('.')[0]) # TODO: -1 or 0 ?
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            for name in node.names:
                if name.name == '*':
                    continue
                defined.add(name.asname or name.name)
            self.generic_visit(node)

        def visit_comprehension(self, node):
            self._add_target_names(node.target)
            self.generic_visit(node)

        def visit_NamedExpr(self, node):
            self._add_target_names(node.target)
            self.generic_visit(node)

    collector = DefinedNameCollector()
    tree = getattr(file_module, 'tree', None)
    if tree is None:
        return ALL_BUILTINS
    collector.visit(tree)
    return ALL_BUILTINS - defined

class ObfBuiltins(ast.NodeTransformer):
    """
    Obfuscates builtins.
    """
    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.builtin_map = {
            b: next(self.randomizer.random_name_gen)
            for b in _collect_defined_names(file_module)
        }

    def builtin_code(self):
        value = ','.join(map(str, self.builtin_map.values()))
        value += '='
        value += ','.join(map(str, self.builtin_map.keys()))
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id='exec', ctx=ast.Load()),
                args=[ast.Constant(value=value)],
                keywords=[]
            )
        )

    def visit_Module(self, node):
        if not self.builtin_map:
            return self.generic_visit(node)

        doc_string = None
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            doc_string = node.body.pop(0)
        insert_position = 0
        for i, n in enumerate(node.body):
            if not isinstance(n, (ast.Import, ast.ImportFrom)):
                insert_position = i
                break
        self.generic_visit(node)
        node.body.insert(insert_position, self.builtin_code())
        if doc_string:
            node.body.insert(0, doc_string)
        return node

    def visit_Name(self, node):
        if node.id in self.builtin_map:
            return ast.Name(
                id=self.builtin_map[node.id],
                ctx=node.ctx
            )
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, (bool, type(None))) and str(node.value) in self.builtin_map:
            return ast.Name(id=self.builtin_map[str(node.value)], ctx=ast.Load())
        return node
