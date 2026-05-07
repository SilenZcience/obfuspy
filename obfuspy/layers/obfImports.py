import ast
import os

from obfuspy.util.domain import SYMBOL_MAP
from obfuspy.util.randomizer import Randomizer


class ObfImports(ast.NodeTransformer):
    """
    Obfuscates import statements and corresponding usages.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.module_name = getattr(file_module, 'module_name', None)
        self._import_alias_stack = []  # Stack of dicts: {local_name: obf_name}
        self._shadowed_names_stack = []  # Stack of sets: names that are shadowed in current scope

    def _push_import_scope(self, node):
        self._import_alias_stack.append({})
        self._collect_import_aliases(node)

    def _pop_import_scope(self):
        if self._import_alias_stack:
            self._import_alias_stack.pop()

    def _current_import_aliases(self):
        return self._import_alias_stack[-1] if self._import_alias_stack else {}

    def _push_shadowed_names_scope(self):
        self._shadowed_names_stack.append(set())

    def _pop_shadowed_names_scope(self):
        if self._shadowed_names_stack:
            self._shadowed_names_stack.pop()

    def _current_shadowed_names(self):
        return self._shadowed_names_stack[-1] if self._shadowed_names_stack else set()

    def _resolve_import_module_name(self, node):
        module_name = self.module_name
        if node.level == 0:
            return node.module

        if not module_name:
            return node.module

        if self.file_module and os.path.basename(self.file_module.in_path) == '__init__.py':
            package_name = module_name
        else:
            package_name = module_name.rsplit('.', 1)[0] if '.' in module_name else ''

        package_parts = package_name.split('.') if package_name else []
        relative_levels = node.level - 1
        if relative_levels > len(package_parts):
            return None
        if relative_levels:
            package_parts = package_parts[:len(package_parts) - relative_levels]

        resolved_package = '.'.join(package_parts)
        if node.module:
            return f"{resolved_package}.{node.module}" if resolved_package else node.module
        return resolved_package or None

    def visit_Module(self, node):
        self._import_alias_stack = []
        self._push_import_scope(node)
        self._push_shadowed_names_scope()
        self.generic_visit(node)
        self._pop_shadowed_names_scope()
        self._pop_import_scope()
        return node

    def visit_ClassDef(self, node):
        self._push_import_scope(node)
        self._current_shadowed_names().add(node.name)
        self._push_shadowed_names_scope()
        self.generic_visit(node)
        self._pop_shadowed_names_scope()
        self._pop_import_scope()
        return node

    def visit_FunctionDef(self, node):
        self._push_import_scope(node)
        self._current_shadowed_names().add(node.name)
        self._push_shadowed_names_scope()
        self.generic_visit(node)
        self._pop_shadowed_names_scope()
        self._pop_import_scope()
        return node

    def visit_AsyncFunctionDef(self, node):
        self._push_import_scope(node)
        self._current_shadowed_names().add(node.name)
        self._push_shadowed_names_scope()
        self.generic_visit(node)
        self._pop_shadowed_names_scope()
        self._pop_import_scope()
        return node

    def _collect_import_aliases(self, node):
        alias_map = self._current_import_aliases()
        for stmt in getattr(node, 'body', []):
            if isinstance(stmt, ast.Import):
                for name in stmt.names:
                    if name.asname is None and '.' in name.name:
                        continue
                    local = name.asname or name.name
                    alias_map[local] = {
                        'asname': next(self.randomizer.random_name_gen),
                    }
            elif isinstance(stmt, ast.ImportFrom):
                for name in stmt.names:
                    if name.name == '*':
                        continue
                    local = name.asname or name.name
                    imported_module = self._resolve_import_module_name(stmt)
                    imported_node = SYMBOL_MAP.find_import(imported_module, name.name)
                    if imported_node and hasattr(imported_node, 'greyed_out'): # indicates that is was actually obfusacted
                        alias_map[local] = {
                            'name': imported_node.obf_value['name'],
                            'asname': next(self.randomizer.random_name_gen),
                        }
                    else:
                        alias_map[local] = {
                            'name': name.name,
                            'asname': next(self.randomizer.random_name_gen),
                        }
            elif isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                # Stop collecting imports in nested scopes
                continue
            else:
                self._collect_import_aliases(stmt)

    def visit_Import(self, node):
        alias_map = self._current_import_aliases()
        for name in node.names:
            local = name.asname or name.name
            if local in alias_map:
                name.asname = alias_map[local]['asname']
        return node

    def visit_ImportFrom(self, node):
        alias_map = self._current_import_aliases()
        for name in node.names:
            local = name.asname or name.name
            if local in alias_map:
                name.name   = alias_map[local]['name']
                name.asname = alias_map[local]['asname']
        return node

    def visit_Assign(self, node):
        shadowed_names = self._current_shadowed_names()
        for target in node.targets:
            if isinstance(target, ast.Name):
                shadowed_names.add(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        shadowed_names.add(elt.id)
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node):
        shadowed_names = self._current_shadowed_names()
        target = node.target
        if isinstance(target, ast.Name):
            shadowed_names.add(target.id)
        self.generic_visit(node)
        return node

    def visit_AugAssign(self, node):
        shadowed_names = self._current_shadowed_names()
        target = node.target
        if isinstance(target, ast.Name):
            shadowed_names.add(target.id)
        self.generic_visit(node)
        return node

    def visit_For(self, node):
        shadowed_names = self._current_shadowed_names()
        target = node.target
        if isinstance(target, ast.Name):
            shadowed_names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    shadowed_names.add(elt.id)
        self.generic_visit(node)
        return node

    def visit_AsyncFor(self, node):
        shadowed_names = self._current_shadowed_names()
        target = node.target
        if isinstance(target, ast.Name):
            shadowed_names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    shadowed_names.add(elt.id)
        self.generic_visit(node)
        return node

    def visit_With(self, node):
        shadowed_names = self._current_shadowed_names()
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                shadowed_names.add(item.optional_vars.id)
        self.generic_visit(node)
        return node

    def visit_AsyncWith(self, node):
        shadowed_names = self._current_shadowed_names()
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                shadowed_names.add(item.optional_vars.id)
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        for import_stack in reversed(self._import_alias_stack):
            if not node.id in import_stack:
                continue
            break
        else:
            return node

        # NOTE: this is not fully working, as the assignement or import can be in a branch .. static analysis would be overkill ...
        # perhaps its fine to just blindly obfuscate everything with that name.
        # for shadowed_stack in reversed(self._shadowed_names_stack):
        #     if node.id in shadowed_stack:
        #         return node

        node.id = import_stack[node.id]['asname']
        return node

    # def visit_Attribute(self, node):
    #     # Obfuscate attribute chains for imported modules (like reference impl)
    #     parts = []
    #     current = node
    #     while isinstance(current, ast.Attribute):
    #         parts.append(current.attr)
    #         current = current.value
    #     if isinstance(current, ast.Name):
    #         for import_stack in reversed(self._import_alias_stack):
    #             if current.id in import_stack:
    #                 # Build full path: import asname + . + attr chain
    #                 obf_base = import_stack[current.id]['asname']
    #                 # Optionally, could also obfuscate attribute chain if needed
    #                 # For now, just replace base name
    #                 current.id = obf_base
    #                 break
    #     self.generic_visit(node)
    #     return node
