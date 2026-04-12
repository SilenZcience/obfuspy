import ast
from obfuspy.util.randomizer import Randomizer, BUILTINS_DEFAULT

class ObfModuleVariables(ast.NodeTransformer): # TODO: verify
    """
    Obfuscates module-level variables.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)
        self.scope_stack = []
        self.current_table_stack = []
        # Caches for performance
        self._cached_module_var_map = None
        self._cached_entry_for_name = {}
        # Blocklist of import names that should not be obfuscated
        self._import_names_blocklist = set()

    def _module_var_exports(self) -> dict:
        return self.project_context.get('symbol_map', {})

    @staticmethod
    def _entry_name(entry):
        if isinstance(entry, dict):
            return entry.get('name')
        return entry

    @staticmethod
    def _entry_kind(entry):
        if isinstance(entry, dict):
            return entry.get('kind')
        return None

    def _current_vars_dict(self) -> dict:
        symbol_map = self.project_context.setdefault('symbol_map', {})
        if isinstance(symbol_map, dict):
            return symbol_map
        return {}

    def _module_var_entry_for_name(self, name: str):
        # Use cache to avoid repeated lookups
        cache = self._cached_entry_for_name
        if name in cache:
            return cache[name]
        module_name = self.module_name
        if module_name is None:
            cache[name] = None
            return None

        exports = self._module_var_exports()
        prefix = f'{module_name}.'
        for qualified_name, entry in exports.items():
            if self._entry_kind(entry) not in (None, 'module_var'):
                continue
            if not qualified_name.startswith(prefix):
                continue
            current_name = self._entry_name(entry)
            original_name = qualified_name.rsplit('.', 1)[-1]
            if name == original_name or name == current_name:
                cache[name] = (qualified_name, current_name)
                return cache[name]
        cache[name] = None
        return None

    def _set_current_module_var_name(self, qualified_name: str, current_name: str) -> None:
        exports = self._current_vars_dict()
        exports[qualified_name] = {'name': current_name, 'kind': 'module_var'}

    def _current_module_var_map(self) -> dict:
        # Cache the map for the lifetime of the instance (or until explicitly invalidated)
        if self._cached_module_var_map is not None:
            return self._cached_module_var_map
        module_name = self.module_name
        if module_name is None:
            self._cached_module_var_map = {}
            return self._cached_module_var_map

        exports = self._module_var_exports()
        prefix = f'{module_name}.'
        result = {
            qualified_name.rsplit('.', 1)[-1]: self._entry_name(entry)
            for qualified_name, entry in exports.items()
            if (
                qualified_name.startswith(prefix)
                and qualified_name.rsplit('.', 1)[-1] not in BUILTINS_DEFAULT
                and self._entry_kind(entry) in (None, 'module_var')
            )
        }
        self._cached_module_var_map = result
        return result
    def _invalidate_caches(self):
        self._cached_module_var_map = None
        self._cached_entry_for_name.clear()

    def _collect_import_names(self, node) -> set:
        """
        Pre-scan the AST to collect all names bound by import statements.
        This prevents obfuscation of variables that share names with imports or import aliases.

        Returns a set of all names that are imported or aliased in import statements.
        """
        import_names = set()

        class ImportCollector(ast.NodeVisitor):
            def visit_Import(self, node):
                for name in node.names:
                    # Add the alias if it exists, otherwise add the first part of the module name
                    if name.asname:
                        import_names.add(name.asname)
                    else:
                        # For 'import x.y.z', only 'x' is bound in the local namespace
                        import_names.add(name.name.split('.')[0])
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                for name in node.names:
                    if name.name == '*':
                        # Can't determine what names are imported with *, skip
                        continue
                    # Add the alias if it exists, otherwise add the imported name
                    if name.asname:
                        import_names.add(name.asname)
                    else:
                        import_names.add(name.name)
                self.generic_visit(node)

        collector = ImportCollector()
        collector.visit(node)
        return import_names

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def _rename_store_target(self, target, source_node):
        module_var_map = self._current_module_var_map()
        aliases = []

        if isinstance(target, ast.Name):
            original_name = target.id
            # Skip obfuscation if the name is in the import blocklist
            if original_name in self._import_names_blocklist:
                return target, aliases
            obfuscated_name = module_var_map.get(original_name)
            if obfuscated_name is not None and original_name not in BUILTINS_DEFAULT:
                entry = self._module_var_entry_for_name(original_name)
                target.id = obfuscated_name
                target.ctx = ast.Store()
                if entry is not None:
                    self._set_current_module_var_name(entry[0], obfuscated_name)
                aliases.append(self._alias_assign(original_name, obfuscated_name, source_node))
            return target, aliases

        if isinstance(target, (ast.Tuple, ast.List)):
            new_elts = []
            for element in target.elts:
                new_element, element_aliases = self._rename_store_target(element, source_node)
                new_elts.append(new_element)
                aliases.extend(element_aliases)
            target.elts = new_elts
            return target, aliases

        return target, aliases

    def _is_module_scope(self) -> bool:
        return not self.scope_stack

    def _current_table(self):
        return self.current_table_stack[-1] if self.current_table_stack else None

    def _child_table_for(self, node, kind: str):
        current_table = self._current_table()
        if current_table is None:
            return None

        candidates = []
        for child in current_table.get_children():
            if child.get_name() == node.name and child.get_lineno() == getattr(node, 'lineno', None):
                candidates.append(child)
        if candidates:
            return candidates[0]

        for child in current_table.get_children():
            if child.get_name() == node.name:
                return child
        return None

    def _is_shadowed(self, name: str) -> bool:
        current_table = self._current_table()
        if current_table is None:
            return False

        try:
            symbol = current_table.lookup(name)
        except KeyError:
            return False

        return symbol.is_local() or symbol.is_parameter() or symbol.is_imported()

    def _is_global_binding(self, name: str) -> bool:
        current_table = self._current_table()
        if current_table is None:
            return False

        try:
            symbol = current_table.lookup(name)
        except KeyError:
            return False

        return symbol.is_global()

    def visit_Module(self, node):
        self.scope_stack = []
        self.current_table_stack = [self.file_module.symtable]
        self._invalidate_caches()
        # Collect import names to avoid obfuscating variables with conflicting names
        self._import_names_blocklist = self._collect_import_names(node)
        self.generic_visit(node)
        self.current_table_stack.pop()
        return node

    def visit_FunctionDef(self, node):
        child_table = self._child_table_for(node, 'function')
        if child_table is not None:
            self.current_table_stack.append(child_table)
        self.scope_stack.append('function')
        self.generic_visit(node)
        self.scope_stack.pop()
        if child_table is not None:
            self.current_table_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        child_table = self._child_table_for(node, 'function')
        if child_table is not None:
            self.current_table_stack.append(child_table)
        self.scope_stack.append('function')
        self.generic_visit(node)
        self.scope_stack.pop()
        if child_table is not None:
            self.current_table_stack.pop()
        return node

    def visit_ClassDef(self, node):
        child_table = self._child_table_for(node, 'class')
        if child_table is not None:
            self.current_table_stack.append(child_table)
        self.scope_stack.append('class')
        self.generic_visit(node)
        self.scope_stack.pop()
        if child_table is not None:
            self.current_table_stack.pop()
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        aliases = []
        new_targets = []

        for target in node.targets:
            if self._is_module_scope():
                new_target, target_aliases = self._rename_store_target(target, node)
            else:
                new_target, target_aliases = self._rename_global_store_target(target, node)
            new_targets.append(new_target)
            aliases.extend(target_aliases)

        node.targets = new_targets
        return [node, *aliases] if aliases else node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        if not self._is_module_scope():
            return node

        node.target, aliases = self._rename_store_target(node.target, node)
        return [node, *aliases] if aliases else node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        if self._is_module_scope():
            node.target, aliases = self._rename_store_target(node.target, node)
            return [node, *aliases] if aliases else node

        # In function scope, mirror `global NAME += expr` without evaluating expr twice.
        if isinstance(node.target, ast.Name):
            original_name = node.target.id
            module_var_map = self._current_module_var_map()
            obfuscated_name = module_var_map.get(original_name)
            if obfuscated_name is not None and self._is_global_binding(original_name):
                obfuscated_aug = ast.AugAssign(
                    target=ast.Name(id=obfuscated_name, ctx=ast.Store()),
                    op=node.op,
                    value=node.value,
                    lineno=getattr(node, 'lineno', 0),
                    col_offset=getattr(node, 'col_offset', 0),
                )
                return [obfuscated_aug, self._alias_assign(original_name, obfuscated_name, node)]

        return node

    def visit_For(self, node):
        self.generic_visit(node)
        if not self._is_module_scope():
            return node

        node.target, aliases = self._rename_store_target(node.target, node)
        return [node, *aliases] if aliases else node

    def visit_AsyncFor(self, node):
        self.generic_visit(node)
        if not self._is_module_scope():
            return node

        node.target, aliases = self._rename_store_target(node.target, node)
        return [node, *aliases] if aliases else node

    def visit_With(self, node):
        self.generic_visit(node)
        if not self._is_module_scope():
            return node

        aliases = []
        for item in node.items:
            if item.optional_vars is None:
                continue
            item.optional_vars, item_aliases = self._rename_store_target(item.optional_vars, node)
            aliases.extend(item_aliases)
        return [node, *aliases] if aliases else node

    def visit_AsyncWith(self, node):
        self.generic_visit(node)
        if not self._is_module_scope():
            return node

        aliases = []
        for item in node.items:
            if item.optional_vars is None:
                continue
            item.optional_vars, item_aliases = self._rename_store_target(item.optional_vars, node)
            aliases.extend(item_aliases)
        return [node, *aliases] if aliases else node

    def _rename_global_store_target(self, target, source_node):
        module_var_map = self._current_module_var_map()
        aliases = []

        if isinstance(target, ast.Name):
            original_name = target.id
            # Skip obfuscation if the name is in the import blocklist
            if original_name in self._import_names_blocklist:
                return target, aliases
            obfuscated_name = module_var_map.get(original_name)
            if obfuscated_name is not None and self._is_global_binding(original_name):
                entry = self._module_var_entry_for_name(original_name)
                target.id = obfuscated_name
                target.ctx = ast.Store()
                if entry is not None:
                    self._set_current_module_var_name(entry[0], obfuscated_name)
                aliases.append(self._alias_assign(original_name, obfuscated_name, source_node))
            return target, aliases

        if isinstance(target, (ast.Tuple, ast.List)):
            new_elts = []
            for element in target.elts:
                new_element, element_aliases = self._rename_global_store_target(element, source_node)
                new_elts.append(new_element)
                aliases.extend(element_aliases)
            target.elts = new_elts
            return target, aliases

        return target, aliases

    def visit_Global(self, node):
        module_var_map = self._current_module_var_map()
        expanded_names = []
        for name in node.names:
            obfuscated_name = module_var_map.get(name)
            if obfuscated_name is not None:
                expanded_names.append(obfuscated_name)
            expanded_names.append(name)
        node.names = list(dict.fromkeys(expanded_names))
        return node

    def visit_Name(self, node):
        module_var_map = self._current_module_var_map()
        if node.id not in module_var_map:
            return node

        if node.id in BUILTINS_DEFAULT:
            return node

        # Skip obfuscation if the name is in the import blocklist
        if node.id in self._import_names_blocklist:
            return node

        if isinstance(node.ctx, ast.Load) and (self._is_module_scope() or not self._is_shadowed(node.id)):
            node.id = module_var_map[node.id]
        return node
