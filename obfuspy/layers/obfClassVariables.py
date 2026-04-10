import ast
from obfuspy.util.randomizer import Randomizer


class ObfClassVariables(ast.NodeTransformer):
    """
    Obfuscates class variables.
    """

    def __init__(self, randomizer: Randomizer, file_module) -> None:
        self.randomizer = randomizer
        self.file_module = file_module
        self.project_context = getattr(randomizer, 'project_context', {})
        self.module_name = getattr(file_module, 'module_name', None)
        self.scope_stack = []
        self.scope_name_stack = []
        self.class_name_stack = []
        self.class_path_stack = []

    def _qualified_name(self, *parts) -> str:
        return '.'.join(part for part in parts if part)

    def _class_var_exports(self) -> dict:
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

    def _current_class_vars_dict(self) -> dict:
        symbol_map = self.project_context.setdefault('symbol_map', {})
        if isinstance(symbol_map, dict):
            return symbol_map
        return {}

    def _class_var_entry_for_name(self, name: str):
        class_path = self._current_class_path()
        if class_path is None:
            return None

        exports = self._class_var_exports()
        prefix = f'{class_path}.'
        for qualified_name, entry in exports.items():
            if self._entry_kind(entry) not in (None, 'class_var'):
                continue
            if not qualified_name.startswith(prefix):
                continue
            current_name = self._entry_name(entry)
            original_name = qualified_name.rsplit('.', 1)[-1]
            if name == original_name or name == current_name:
                return qualified_name, current_name
        return None

    def _set_current_class_var_name(self, qualified_name: str, current_name: str) -> None:
        exports = self._current_class_vars_dict()
        exports[qualified_name] = {'name': current_name, 'kind': 'class_var'}

    def _current_class_path(self):
        return self.class_path_stack[-1] if self.class_path_stack else None

    def _current_class_name(self):
        return self.class_name_stack[-1] if self.class_name_stack else None

    def _current_class_var_map(self) -> dict:
        class_path = self._current_class_path()
        if class_path is None:
            return {}

        exports = self._class_var_exports()
        prefix = f'{class_path}.'
        return {
            qualified_name.rsplit('.', 1)[-1]: self._entry_name(entry)
            for qualified_name, entry in exports.items()
            if qualified_name.startswith(prefix) and self._entry_kind(entry) in (None, 'class_var')
        }

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def _is_in_class_scope(self) -> bool:
        return bool(self.scope_stack) and self.scope_stack[-1] == 'class'

    def visit_Module(self, node):
        self.scope_stack = []
        self.scope_name_stack = []
        self.class_name_stack = []
        self.class_path_stack = []
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.scope_stack.append('class')
        self.class_name_stack.append(node.name)
        self.class_path_stack.append(self._qualified_name(self.module_name, *self.scope_name_stack, node.name))
        self.scope_name_stack.append(node.name)

        new_body = []
        for stmt in node.body:
            processed_stmt = self.visit(stmt)
            if isinstance(processed_stmt, list):
                new_body.extend(processed_stmt)
            elif processed_stmt is not None:
                new_body.append(processed_stmt)

        node.body = new_body

        self.scope_name_stack.pop()
        self.class_path_stack.pop()
        self.class_name_stack.pop()
        self.scope_stack.pop()
        return node

    def visit_FunctionDef(self, node):
        self.scope_stack.append('function')
        self.scope_name_stack.append(node.name)
        self.generic_visit(node)
        self.scope_name_stack.pop()
        self.scope_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.scope_stack.append('function')
        self.scope_name_stack.append(node.name)
        self.generic_visit(node)
        self.scope_name_stack.pop()
        self.scope_stack.pop()
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if not self._is_in_class_scope():
            return node

        aliases = []
        class_var_map = self._current_class_var_map()
        new_targets = []

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in class_var_map:
                original_name = target.id
                obfuscated_name = class_var_map[original_name]
                entry = self._class_var_entry_for_name(original_name)
                target.id = obfuscated_name
                target.ctx = ast.Store()
                if entry is not None:
                    self._set_current_class_var_name(entry[0], obfuscated_name)
                new_targets.append(target)
                aliases.append(self._alias_assign(original_name, obfuscated_name, node))
            else:
                new_targets.append(target)

        node.targets = new_targets
        return [node, *aliases] if aliases else node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        if not self._is_in_class_scope():
            return node

        if isinstance(node.target, ast.Name):
            class_var_map = self._current_class_var_map()
            original_name = node.target.id
            obfuscated_name = class_var_map.get(original_name)
            if obfuscated_name is not None:
                entry = self._class_var_entry_for_name(original_name)
                node.target.id = obfuscated_name
                node.target.ctx = ast.Store()
                if entry is not None:
                    self._set_current_class_var_name(entry[0], obfuscated_name)
                alias = self._alias_assign(original_name, obfuscated_name, node)
                return [node, alias]
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        if not self._is_in_class_scope():
            return node

        if isinstance(node.target, ast.Name):
            class_var_map = self._current_class_var_map()
            original_name = node.target.id
            obfuscated_name = class_var_map.get(original_name)
            if obfuscated_name is not None:
                entry = self._class_var_entry_for_name(original_name)
                node.target.id = obfuscated_name
                node.target.ctx = ast.Store()
                if entry is not None:
                    self._set_current_class_var_name(entry[0], obfuscated_name)
                alias = self._alias_assign(original_name, obfuscated_name, node)
                return [node, alias]
        return node

    def visit_Name(self, node):
        if self._is_in_class_scope() and isinstance(node.ctx, ast.Load):
            class_var_map = self._current_class_var_map()
            if node.id in class_var_map:
                node.id = class_var_map[node.id]
        return node

    def visit_Attribute(self, node):
        if not self.class_name_stack:
            return self.generic_visit(node)

        class_var_map = self._current_class_var_map()
        if not class_var_map:
            return self.generic_visit(node)

        root = node
        attr_parts = []
        while isinstance(root, ast.Attribute):
            attr_parts.append(root.attr)
            root = root.value

        if isinstance(root, ast.Name):
            current_class_name = self._current_class_name()
            if root.id in {'self', 'cls', current_class_name} and node.attr in class_var_map:
                node.attr = class_var_map[node.attr]

        self.generic_visit(node)
        return node
