import ast
from obfuspy.util.randomizer import Randomizer


class ObfImports(ast.NodeTransformer):
    """
    Obfuscates import-statements.
    """
    global_import_map = {}  # Class variable: Maps module names to their global obfuscated aliases

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.import_map = {}
        self.binding_map = {}
        self.explicit_global_stack = []
        self.scope_name_stack = []

    def _resolve_import_module(self, node) -> str:
        module_name = getattr(self.file_module, 'module_name', None)
        node_module = getattr(node, 'module', None)
        if module_name is None:
            return node_module

        current_parts = module_name.split('.')
        base_parts = current_parts[:-1]
        level = getattr(node, 'level', 0)

        if level > 1:
            base_parts = base_parts[:max(0, len(base_parts) - (level - 1))]

        module_parts = list(base_parts)
        if node_module:
            module_parts.extend(node_module.split('.'))
        return '.'.join(part for part in module_parts if part)

    def _export_name(self, qualified_name: str):
        entry = self.project_context.get('symbol_map', {}).get(qualified_name)
        if isinstance(entry, dict):
            return entry.get('name')
        return entry

    def _qualified_name(self, *parts) -> str:
        return '.'.join(part for part in parts if part)

    def _scope_key(self) -> tuple:
        return tuple(self.scope_name_stack)

    def _register_import(self, scope_key: tuple, original_name: str, local_name: str) -> None:
        self.import_map.setdefault(scope_key, {})[original_name] = local_name

    def _lookup_import(self, original_name: str):
        for end_index in range(len(self.scope_name_stack), -1, -1):
            scope_key = tuple(self.scope_name_stack[:end_index])
            scope_map = self.import_map.get(scope_key)
            if scope_map is not None and original_name in scope_map:
                return scope_map[original_name]
        return None

    def _local_import_name(self, preferred_name: str, module_key: str = None) -> str:
        """
        Generate or retrieve a local import alias name.

        If module_key is provided and already exists in the global import map,
        reuse that alias. Otherwise, generate a new unique name and store it
        in the global map if module_key is provided.
        """
        # If we have a module key and it's already been aliased, reuse that alias
        if module_key and module_key in ObfImports.global_import_map:
            return ObfImports.global_import_map[module_key]

        # Generate a new unique name
        generated_name = next(self.randomizer.random_name_gen)
        while generated_name == preferred_name:
            generated_name = next(self.randomizer.random_name_gen)

        # Store in global map if module_key is provided
        if module_key:
            ObfImports.global_import_map[module_key] = generated_name

        return generated_name

    def _collect_import_bindings(self, node) -> None:
        if isinstance(node, ast.ClassDef):
            self.scope_name_stack.append(node.name)
            for child in node.body:
                self._collect_import_bindings(child)
            self.scope_name_stack.pop()
            return

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.scope_name_stack.append(node.name)
            for child in node.body:
                self._collect_import_bindings(child)
            self.scope_name_stack.pop()
            return

        if isinstance(node, ast.Import):
            scope_key = self._scope_key()
            for name in node.names:
                original_bound_name = name.asname or name.name.split('.')[0]
                if name.asname is None and '.' in name.name:
                    continue
                # Use the full module name as the key for consistent aliasing
                module_key = self._qualified_name(self._resolve_import_module(node), name.name)
                local_name = self._local_import_name(name.name.split('.')[-1], module_key=module_key)
                self._register_import(scope_key, original_bound_name, local_name)
                self.binding_map[local_name] = module_key
            return

        if isinstance(node, ast.ImportFrom):
            scope_key = self._scope_key()
            resolved_module = self._resolve_import_module(node)
            for name in node.names:
                if name.name == '*':
                    continue
                original_bound_name = name.asname or name.name
                qualified_name = f'{resolved_module}.{name.name}' if resolved_module else name.name
                export_name = self._export_name(qualified_name)
                imported_symbol_name = export_name if export_name is not None else name.name
                # Use the qualified name as the key for consistent aliasing
                local_name = self._local_import_name(imported_symbol_name, module_key=qualified_name)
                self._register_import(scope_key, original_bound_name, local_name)
                self.binding_map[local_name] = qualified_name
            return

        for field_name in ('body', 'orelse', 'finalbody'):
            child_body = getattr(node, field_name, None)
            if child_body:
                for child in child_body:
                    self._collect_import_bindings(child)
        for handler in getattr(node, 'handlers', []):
            for child in handler.body:
                self._collect_import_bindings(child)

    def visit_Module(self, node):
        ObfImports.global_import_map = {}
        self.import_map = {}
        self.binding_map = {}
        self.explicit_global_stack = []
        self.scope_name_stack = []
        self._collect_import_bindings(node)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.scope_name_stack.append(node.name)
        self.generic_visit(node)
        self.scope_name_stack.pop()
        return node

    def visit_FunctionDef(self, node):
        self.scope_name_stack.append(node.name)
        self.explicit_global_stack.append(set())
        self.generic_visit(node)
        self.explicit_global_stack.pop()
        self.scope_name_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.scope_name_stack.append(node.name)
        self.explicit_global_stack.append(set())
        self.generic_visit(node)
        self.explicit_global_stack.pop()
        self.scope_name_stack.pop()
        return node

    def _in_module_scope(self) -> bool:
        return not self.explicit_global_stack

    def _is_explicit_global_name(self, name: str) -> bool:
        return bool(self.explicit_global_stack) and name in self.explicit_global_stack[-1]

    def visit_Import(self, node):
        for name in node.names:
            original_bound_name = name.asname or name.name.split('.')[0]
            local_name = self._lookup_import(original_bound_name)

            if local_name is None:
                if name.asname is None and '.' in name.name:
                    self.binding_map[original_bound_name] = self._qualified_name(self._resolve_import_module(node), name.name)
                    continue
                # Use the full module name as the key for consistent aliasing
                module_key = self._qualified_name(self._resolve_import_module(node), name.name)
                local_name = self._local_import_name(name.name.split('.')[-1], module_key=module_key)
                self._register_import(self._scope_key(), original_bound_name, local_name)
                self.binding_map[local_name] = module_key

            if name.asname is None and '.' in name.name:
                continue

            name.asname = local_name
        return node

    def visit_ImportFrom(self, node):
        resolved_module = self._resolve_import_module(node)
        for name in node.names:
            if name.name == '*':
                continue

            original_bound_name = name.asname or name.name
            qualified_name = f'{resolved_module}.{name.name}' if resolved_module else name.name
            export_name = self._export_name(qualified_name)
            imported_symbol_name = export_name if export_name is not None else name.name

            local_name = self._lookup_import(original_bound_name)
            if local_name is None:
                # Use the qualified name as the key for consistent aliasing
                local_name = self._local_import_name(imported_symbol_name, module_key=qualified_name)
                self._register_import(self._scope_key(), original_bound_name, local_name)
                self.binding_map[local_name] = qualified_name

            name.name = imported_symbol_name
            name.asname = local_name
        return node

    def visit_Global(self, node):
        new_names = []
        current_globals = self.explicit_global_stack[-1] if self.explicit_global_stack else None
        for name in node.names:
            if current_globals is not None:
                current_globals.add(name)

            mapped = self._lookup_import(name)
            if mapped is not None:
                new_names.append(mapped)
                if current_globals is not None:
                    current_globals.add(mapped)
            else:
                new_names.append(name)
        node.names = new_names
        return node

    def visit_Nonlocal(self, node):
        new_names = []
        for name in node.names:
            mapped = self._lookup_import(name)
            if mapped is not None:
                new_names.append(mapped)
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

        if isinstance(current, ast.Name) and current.id in self.binding_map:
            module_path = self.binding_map[current.id]
            attr_parts = list(reversed(parts))
            module_parts = module_path.split('.') if module_path else []

            overlap = 0
            max_overlap = min(len(module_parts), len(attr_parts))
            for size in range(max_overlap, 0, -1):
                if module_parts[-size:] == attr_parts[:size]:
                    overlap = size
                    break

            candidate_parts = module_parts + attr_parts[overlap:]
            if candidate_parts:
                export_name = self._export_name('.'.join(candidate_parts))
                if export_name is not None:
                    node.attr = export_name

        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        mapped_name = self._lookup_import(node.id)
        if mapped_name is None:
            return node

        if isinstance(node.ctx, ast.Load):
            return ast.Name(id=mapped_name, ctx=node.ctx)

        if isinstance(node.ctx, ast.Store) and (self._in_module_scope() or self._is_explicit_global_name(node.id)):
            return ast.Name(id=mapped_name, ctx=node.ctx)

        return node

    def visit_Delete(self, node):
        for idx, target in enumerate(node.targets):
            if isinstance(target, ast.Name):
                mapped_name = self._lookup_import(target.id)
                if mapped_name is not None:
                    node.targets[idx] = ast.Name(id=mapped_name, ctx=ast.Del())
        self.generic_visit(node)
        return node
