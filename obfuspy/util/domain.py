

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
