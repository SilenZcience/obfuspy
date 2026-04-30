class Label:
    ltype = ''

    def __init__(self, name: str):
        self.name = name

    def set_name(self, new_name: str):
        self.name = new_name

    @staticmethod
    def copy(other):
        new_label = Label(other.name)
        new_label.ltype = other.ltype
        return new_label

    def __repr__(self):
        return f"{self.ltype}{self.name}"


class Node: # fake node, its actually a label
    class Module(Label):
        ltype = 'module.'
        def set_name(self, _):
            raise ValueError(f"Cannot rename module label '{self.name}'")
    class Cls(Label):
        ltype = 'class.'
    class Def(Label):
        ltype = 'function.'
    class ModVar(Label):
        ltype = 'modulevar.'
    class ClassVar(Label):
        ltype = 'classvar.'
    class DefArg(Label):
        ltype = 'defarg.'


class _Node:
    def __init__(self, label: Label=None, parent=None):
        self.label: Label = label
        self.parent: _Node = parent
        self.children: dict[str, list[_Node]] = {}
        self.obf_value: dict | None = None

    def add_child(self, label: Label, node=None):
        if node is None:
            node = _Node(label, parent=self)
        self.children.setdefault(label.ltype + label.name, []).append(node)
        return node

    def __repr__(self):
        return str(self.label)


class SymbolMap:
    randomizer = None

    def __init__(self):
        self.root = _Node()

    @staticmethod
    def set_randomizer(randomizer):
        SymbolMap.randomizer = randomizer

    def insert(self, parts: list[Label], value: dict):
        node = self.root

        for part in parts:
            candidates = node.children.get(part.ltype + part.name)

            if not candidates:
                node = node.add_child(part)
            else:
                # disambiguation strategy: first match
                # (can be replaced with stricter logic)
                node = candidates[0]

        value['original'] = node.label.name
        node.obf_value = value

    def _get_ltypes(self, label_path: list[Label], ltype: str) -> dict:
        node = self.root
        for label in label_path:
            candidates = node.children.get(str(label))
            if not candidates:
                return {}
            node = candidates[0]

        result = {}
        append_children = {}
        for _, child_nodes in node.children.items():
            for child in child_nodes:
                if getattr(child.label, 'ltype', None) == ltype and not hasattr(child, 'greyed_out'):
                    child.greyed_out = True # marked to not obfusacte again, to avoid exponential growth
                    orig_name = child.label.name
                    if child.obf_value:
                        result[orig_name] = child.obf_value
                        obf_val = child.obf_value['name'] if child.obf_value and 'name' in child.obf_value else orig_name
                        if not child.label.ltype + obf_val in node.children:
                            append_children[obf_val] = child
        for name, child in append_children.items():
            new_label = Label(name)
            new_label.ltype = child.label.ltype
            new_child = _Node(new_label, parent=node)
            new_child.obf_value = {
                'name': next(SymbolMap.randomizer.random_name_gen),
                'original': child.obf_value['original'] if child.obf_value and 'original' in child.obf_value else child.label.name
            }
            new_child.children = child.children
            node.add_child(new_label, new_child)
        return result

    def get_classes(self, label_path: list[Label]) -> dict:
        """
        Given a list of Label objects representing the path to a node,
        return a dict {original_name: obfuscated_name} for all direct class children.
        """
        return self._get_ltypes(label_path, Node.Cls.ltype)

    def get_functions(self, label_path: list[Label]) -> dict:
        """
        Given a list of Label objects representing the path to a node,
        return a dict {original_name: obfuscated_name} for all direct function children.
        """
        return self._get_ltypes(label_path, Node.Def.ltype)

    def get_modulevars(self, label_path: list[Label]) -> dict:
        """
        Given a list of Label objects representing the path to a node,
        return a dict {original_name: obfuscated_name} for all direct modulevar children.
        """
        return self._get_ltypes(label_path, Node.ModVar.ltype)

    def get_classvars(self, label_path: list[Label]) -> dict:
        """
        Given a list of Label objects representing the path to a node,
        return a dict {original_name: obfuscated_name} for all direct classvar children.
        """
        return self._get_ltypes(label_path, Node.ClassVar.ltype)

    def get_defargs(self, label_path: list[Label]) -> dict:
        """
        Given a list of Label objects representing the path to a node,
        return a dict {original_name: obfuscated_name} for all direct defarg children.
        """
        return self._get_ltypes(label_path, Node.DefArg.ltype)

    def get(self, label_path: list[Label]):
        node = self.root
        for label in label_path:
            candidates = node.children.get(str(label))
            if not candidates:
                return None
            node = candidates[0]
        return node.obf_value

    def find_import(self, module_name: str, name: str):
        module_name_split = module_name.split('.')
        for i in range(len(module_name_split)):
            suffix = '.'.join(module_name_split[i:])
            candidates = self.root.children.get(Node.Module.ltype + suffix)
            if candidates:
                break
        else:
            return None
        module_node = candidates[0]
        candidates = (
            module_node.children.get(Node.Cls.ltype + name, []) +
            module_node.children.get(Node.Def.ltype + name, []) +
            module_node.children.get(Node.ModVar.ltype + name, [])
        )
        if not candidates:
            return None
        return candidates[0]

    def _get(self, label_path: list[Label], ltype: str):
        node = self.root
        for label in label_path:
            candidates = node.children.get(str(label))
            if not candidates:
                return None
            node = candidates[0]
        if getattr(node.label, 'ltype', None) == ltype and node.obf_value:
            return node.obf_value

    def get_class(self, label_path: list[Label]):
        """
        Given a list of Label objects representing the path to a node,
        return the obfuscation value for the class at that node, or None if not found
        """
        return self._get(label_path, Node.Cls.ltype)

    def get_function(self, label_path: list[Label]):
        """
        Given a list of Label objects representing the path to a node,
        return the obfuscation value for the function at that node, or None if not found
        """
        return self._get(label_path, Node.Def.ltype)

    def get_modulevar(self, label_path: list[Label]):
        """
        Given a list of Label objects representing the path to a node,
        return the obfuscation value for the module variable at that node, or None if not found
        """
        return self._get(label_path, Node.ModVar.ltype)

    def get_classvar(self, label_path: list[Label]):
        """
        Given a list of Label objects representing the path to a node,
        return the obfuscation value for the class variable at that node, or None if not found
        """
        return self._get(label_path, Node.ClassVar.ltype)

    def get_defarg(self, label_path: list[Label]):
        """
        Given a list of Label objects representing the path to a node,
        return the obfuscation value for the default argument at that node, or None if not found
        """
        return self._get(label_path, Node.DefArg.ltype)

    def __contains__(self, label_path: list[Label]):
        return self.get(label_path) is not None

    def __repr__(self):
        lines = []

        def walk(node, prefix="", is_last=True):
            if node.label is not None:
                connector = "└── " if is_last else "├── "
                label = node.label.ltype + node.label.name

                if node.obf_value is not None:
                    label += f" {node.obf_value}"

                lines.append(prefix + connector + label)
                prefix += "    " if is_last else "│   "

            # flatten children lists for traversal
            all_children = []
            for lst in node.children.values():
                all_children.extend(lst)

            for i, child in enumerate(all_children):
                walk(child, prefix, i == len(all_children) - 1)

        # start from root
        root_children = []
        for lst in self.root.children.values():
            root_children.extend(lst)

        for i, child in enumerate(root_children):
            walk(child, "", i == len(root_children) - 1)

        return "\n".join(lines)

SYMBOL_MAP = SymbolMap()


class File_Module:
    def __init__(self, in_path: str, out_path: str, module_name: str = None) -> None:
        self.in_path = in_path
        self.out_path = out_path
        self.module_name = module_name
        with open(in_path, 'r', encoding='utf-8') as f:
            self.in_code = f.read()
        self.out_code = ''
        self.symtable = None
        self.tree = None

    def set_code(self, code: str) -> None:
        self.out_code = code

    def set_symtable(self, symtable) -> None:
        self.symtable = symtable

    def set_tree(self, tree: str) -> None:
        self.tree = tree

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.in_path}"

    def __hash__(self) -> int:
        return hash(self.in_path)

    def __eq__(self, other) -> bool:
        return self.in_path == other.in_path
