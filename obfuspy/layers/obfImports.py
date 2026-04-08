import ast
from obfuspy.util.randomizer import Randomizer



class ObfImports(ast.NodeTransformer):
    """
    Obfuscates import-statements.
    """
    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.import_map = {}
        self.binding_map = {}
        self.project_context = getattr(randomizer, 'project_context', {})
        self.explicit_global_stack = []

    def _resolve_import_module(self, node) -> str:
        module_name = getattr(self.file_module, 'module_name', None)
        if module_name is None:
            return node.module

        current_parts = module_name.split('.')
        base_parts = current_parts[:-1]

        if node.level > 1:
            base_parts = base_parts[:max(0, len(base_parts) - (node.level - 1))]

        module_parts = list(base_parts)
        if node.module:
            module_parts.extend(node.module.split('.'))
        return '.'.join(part for part in module_parts if part)

    def _export_name(self, qualified_name: str):
        exports = self.project_context.get('exports', {})
        class_vars = self.project_context.get('class_vars', {})
        module_vars = self.project_context.get('vars', {})
        return exports.get(qualified_name) or class_vars.get(qualified_name) or module_vars.get(qualified_name)

    def _local_import_name(self, preferred_name: str) -> str:
        generated_name = next(self.randomizer.random_name_gen)
        while generated_name == preferred_name:
            generated_name = next(self.randomizer.random_name_gen)
        return generated_name

    def visit_Module(self, node):
        self.import_map = {}
        self.binding_map = {}
        self.explicit_global_stack = []
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        self.explicit_global_stack.append(set())
        self.generic_visit(node)
        self.explicit_global_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.explicit_global_stack.append(set())
        self.generic_visit(node)
        self.explicit_global_stack.pop()
        return node

    def _in_module_scope(self) -> bool:
        return not self.explicit_global_stack

    def _is_explicit_global_name(self, name: str) -> bool:
        return bool(self.explicit_global_stack) and name in self.explicit_global_stack[-1]

    def visit_Import(self, node):
        for name in node.names:
            original_bound_name = name.asname or name.name.split('.')[0]
            if name.asname is None and '.' in name.name:
                self.binding_map[original_bound_name] = name.name
                continue
            local_name = self._local_import_name(name.name.split('.')[-1])
            self.import_map[original_bound_name] = local_name
            name.asname = local_name
            self.binding_map[local_name] = name.name
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
            local_name = self._local_import_name(imported_symbol_name)

            self.import_map[original_bound_name] = local_name
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
            if name in self.import_map:
                mapped = self.import_map[name]
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
        if node.id not in self.import_map:
            return node

        if isinstance(node.ctx, ast.Load):
            return ast.Name(
                id=self.import_map[node.id],
                ctx=node.ctx
            )

        if isinstance(node.ctx, ast.Store) and (self._in_module_scope() or self._is_explicit_global_name(node.id)):
            return ast.Name(
                id=self.import_map[node.id],
                ctx=node.ctx
            )
        return node
