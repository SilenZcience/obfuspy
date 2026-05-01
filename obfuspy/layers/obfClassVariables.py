import ast

from obfuspy.util.domain import SYMBOL_MAP, Node


class ObfClassVariables(ast.NodeTransformer):
    """
    Obfuscates class variables.
    """

    FIRST_PASS = True

    def __init__(self, _, file_module) -> None:
        self.module_name = getattr(file_module, 'module_name', None)
        self.prefix_parts = []
        self.scope_stack = [] # Stack of 'module', 'class', 'function
        self._classvar_name_map_stack = []  # Stack of dicts: {original_name: obf_value}
        self._classvar_name_map_cache = {}

    def _push_classvar_scope(self):
        key = tuple((lbl.ltype, lbl.name) for lbl in self.prefix_parts)
        if key in self._classvar_name_map_cache:
            classvar_map = self._classvar_name_map_cache[key]
        else:
            classvar_map = SYMBOL_MAP.get_classvars(self.prefix_parts)
            self._classvar_name_map_cache[key] = classvar_map
        self._classvar_name_map_stack.append(classvar_map)

    def _pop_classvar_scope(self):
        if self._classvar_name_map_stack:
            self._classvar_name_map_stack.pop()

    def _current_classvar_name_map(self):
        return self._classvar_name_map_stack[-1] if self._classvar_name_map_stack else {}

    def _alias_assign(self, original_name: str, obfuscated_name: str, source_node) -> ast.Assign:
        return ast.Assign(
            targets=[ast.Name(id=original_name, ctx=ast.Store())],
            value=ast.Name(id=obfuscated_name, ctx=ast.Load()),
            lineno=getattr(source_node, 'lineno', 0),
            col_offset=getattr(source_node, 'col_offset', 0),
        )

    def visit_Module(self, node):
        self.prefix_parts = [Node.Module(self.module_name)]
        self.scope_stack.append('module')
        self._classvar_name_map_stack = []
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        self.prefix_parts.append(Node.Cls(node.name))
        self.scope_stack.append('class')
        self._push_classvar_scope()

        new_body = []
        for stmt in node.body:
            processed_stmt = self.visit(stmt)
            if isinstance(processed_stmt, list):
                new_body.extend(processed_stmt)
            elif processed_stmt is not None:
                new_body.append(processed_stmt)

        node.body = new_body

        self._pop_classvar_scope()
        self.scope_stack.pop()
        self.prefix_parts.pop()
        return node

    def visit_FunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        self.scope_stack.append('function')
        self.generic_visit(node)
        self.scope_stack.pop()
        self.prefix_parts.pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        self.prefix_parts.append(Node.Def(node.name))
        self.scope_stack.append('function')
        self.generic_visit(node)
        self.scope_stack.pop()
        self.prefix_parts.pop()
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        class_var_map = self._current_classvar_name_map() if self._classvar_name_map_stack else {}
        aliases = []
        new_targets = []
        for target in node.targets: # default assign can have multiple targets
            if isinstance(target, ast.Name) and target.id in class_var_map:
                original_name = target.id
                obfuscated_name = class_var_map[original_name]['name']
                target.id = obfuscated_name
                target.ctx = ast.Store()
                new_targets.append(target)
                aliases.append(self._alias_assign(original_name, obfuscated_name, node))
            else:
                new_targets.append(target)
        node.targets = new_targets
        return [node, *aliases] if aliases else node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        class_var_map = self._current_classvar_name_map() if self._classvar_name_map_stack else {}
        if isinstance(node.target, ast.Name) and node.target.id in class_var_map:
            original_name = node.target.id
            obfuscated_name = class_var_map[original_name]['name']
            node.target.id = obfuscated_name
            node.target.ctx = ast.Store()
            alias = self._alias_assign(original_name, obfuscated_name, node)
            return [node, alias]
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        class_var_map = self._current_classvar_name_map() if self._classvar_name_map_stack else {}
        if isinstance(node.target, ast.Name) and node.target.id in class_var_map:
            original_name = node.target.id
            obfuscated_name = class_var_map[original_name]['name']
            node.target.id = obfuscated_name
            node.target.ctx = ast.Store()
            alias = self._alias_assign(original_name, obfuscated_name, node)
            return [node, alias]
        return node

    def visit_Name(self, node):
        """
        e.g.
        class X:
            var1 = 1
            var2 = var1 * 2 # var1 needs to be obfuscated

        """
        # Only obfuscate class variable loads if in class scope and 100% sure
        if ObfClassVariables.FIRST_PASS and self.scope_stack[-1] == 'class' and isinstance(node.ctx, ast.Load):
            class_var_map = self._current_classvar_name_map()
            if node.id in class_var_map:
                node.id = class_var_map[node.id]['name']
        return node

    def _resolve_classvar_from_attr(self, attr_node):
        # Returns the obfuscated name for a classvar attribute chain, or None if not resolvable
        if not self.module_name:
            return None
        names = []
        node = attr_node
        while isinstance(node, ast.Attribute):
            names.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            names.append(node.id)
        else:
            return None
        names = list(reversed(names))
        # Special case: self.x or cls.x in class scope
        if names[0] in ('self', 'cls') and len(names) == 2 and self._classvar_name_map_stack:
            var_name = names[1]
            class_var_map = self._current_classvar_name_map()
            if var_name in class_var_map:
                return class_var_map[var_name]['name']

        label_path = [Node.Module(self.module_name)]
        for i in range(0, len(names)-1):
            label_path.append(Node.Cls(names[i]))
        label_path.append(Node.ClassVar.ltype + names[-1])
        obf_value = SYMBOL_MAP.get(label_path)
        if obf_value:
            return obf_value['name']
        return None

    def visit_Attribute(self, node):
        obf_name = self._resolve_classvar_from_attr(node)
        if obf_name:
            node.attr = obf_name
        self.generic_visit(node)
        return node
