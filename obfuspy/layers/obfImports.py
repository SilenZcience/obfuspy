import ast

from obfuspy.util.domain import SYMBOL_MAP
from obfuspy.util.randomizer import Randomizer


class ObfImports(ast.NodeTransformer): # TODO: is_shadowed logic
    """
    Obfuscates import statements and corresponding usages.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.module_name = getattr(file_module, 'module_name', None)
        self._import_alias_stack = []  # Stack of dicts: {local_name: obf_name}

    def _push_import_scope(self):
        self._import_alias_stack.append({})

    def _pop_import_scope(self):
        if self._import_alias_stack:
            self._import_alias_stack.pop()

    def _current_import_aliases(self):
        return self._import_alias_stack[-1] if self._import_alias_stack else {}

    def visit_Module(self, node):
        self._import_alias_stack = []
        self._push_import_scope()
        self._collect_import_aliases(node)
        self.generic_visit(node)
        self._pop_import_scope()
        return node

    def visit_ClassDef(self, node):
        self._push_import_scope()
        self._collect_import_aliases(node)
        self.generic_visit(node)
        self._pop_import_scope()
        return node

    def visit_FunctionDef(self, node):
        self._push_import_scope()
        self._collect_import_aliases(node)
        self.generic_visit(node)
        self._pop_import_scope()
        return node

    def visit_AsyncFunctionDef(self, node):
        self._push_import_scope()
        self._collect_import_aliases(node)
        self.generic_visit(node)
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
                    imported_node = SYMBOL_MAP.find_import(stmt.module, name.name)
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

    def visit_Name(self, node):
        for import_stack in reversed(self._import_alias_stack):
            if not node.id in import_stack:
                continue
            node.id = import_stack[node.id]['asname']
            break
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
