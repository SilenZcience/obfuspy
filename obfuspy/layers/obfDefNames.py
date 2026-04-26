import ast
import random
from obfuspy.util.randomizer import Randomizer, BUILTINS_DEFAULT


class ObfDefnames(ast.NodeTransformer): # TODO: verify
    """
    Obfuscates function names.
    """
    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)

        self.scope_name_stack = []
        self.scope_stack = [{}]

        self.class_context_stack = []
        self.class_method_map = {}

    # --------------------------------------------------
    # project_context
    # --------------------------------------------------
    def _export_name_for(self, qualified_name: str):
        entry = self.project_context.get('symbol_map', {}).get(qualified_name)
        if isinstance(entry, dict):
            return entry.get('name')
        return entry

    def _set_export_name_for(self, qualified_name: str, obfuscated_name: str):
        self.project_context.setdefault('symbol_map', {})[qualified_name] = {
            'name': obfuscated_name,
            'kind': 'export'
        }

    # --------------------------------------------------
    # scope
    # --------------------------------------------------
    def _bind(self, name, qn):
        self.scope_stack[-1][name] = qn

    def _resolve(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return None

    def _enter_scope(self):
        self.scope_stack.append({})

    def _exit_scope(self):
        self.scope_stack.pop()

    def _qualified_callable_name(self, name):
        return ".".join([self.module_name] + self.scope_name_stack + [name])

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    # --------------------------------------------------
    # Module
    # --------------------------------------------------
    def visit_Module(self, node):
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()
        return node

    # --------------------------------------------------
    # Class (FIXED: two-phase processing)
    # --------------------------------------------------
    def visit_ClassDef(self, node):
        class_name = node.name

        self.scope_name_stack.append(class_name)
        self._enter_scope()

        method_map = {}

        new_body = []

        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # DO NOT TOUCH child.name here
                new_body.append(child)
            else:
                new_body.append(child)

        node.body = new_body

        self.class_context_stack.append((class_name, method_map))
        self.class_method_map[class_name] = method_map

        self.generic_visit(node)

        self.class_context_stack.pop()
        self._exit_scope()
        self.scope_name_stack.pop()

        return node

    # --------------------------------------------------
    # Functions
    # --------------------------------------------------
    def _visit_function(self, node):
        original = node.name
        qn = self._qualified_callable_name(original)

        obf = self._export_name_for(qn)

        if obf is not None:
            if self.class_context_stack:
                class_name = self.class_context_stack[-1][0]
                self.class_method_map.setdefault(class_name, {})[original] = obf

            node.name = obf
            self._bind(original, qn)

            self.scope_name_stack.append(original)
            self._enter_scope()

            for arg in node.args.args:
                self._bind(arg.arg, None)

            self.generic_visit(node)

            self._exit_scope()
            self.scope_name_stack.pop()

            return [node, self._alias_assign(original, obf, node)]

        self.scope_name_stack.append(original)
        self._enter_scope()

        self.generic_visit(node)

        self._exit_scope()
        self.scope_name_stack.pop()

        return node

    def visit_FunctionDef(self, node):
        return self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_function(node)

    # --------------------------------------------------
    # Assignments / loops
    # --------------------------------------------------
    def visit_Assign(self, node):
        self.visit(node.value)
        for t in node.targets:
            self._bind_target(t)
            self.visit(t)
        return node

    def visit_For(self, node):
        self.visit(node.iter)
        self._bind_target(node.target)
        self.visit(node.target)
        for s in node.body:
            self.visit(s)
        return node

    def _bind_target(self, target):
        if isinstance(target, ast.Name):
            self._bind(target.id, None)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for e in target.elts:
                self._bind_target(e)

    # --------------------------------------------------
    # Name resolution
    # --------------------------------------------------
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            qn = self._resolve(node.id)
            if qn:
                obf = self._export_name_for(qn)
                if obf:
                    node.id = obf
        return node

    # --------------------------------------------------
    # Attributes
    # --------------------------------------------------
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            cls = node.value.id
            if cls in self.class_method_map:
                m = self.class_method_map[cls]
                if node.attr in m:
                    node.attr = m[node.attr]

        elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            cls = node.value.func.id
            if cls in self.class_method_map:
                m = self.class_method_map[cls]
                if node.attr in m:
                    node.attr = m[node.attr]

        self.generic_visit(node)
        return node
