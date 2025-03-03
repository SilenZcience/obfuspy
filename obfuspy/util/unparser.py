
import ast

def unparse(ast_obj, obfuscate_indentation=False, indentation_string=' ' * 4):
    class Builder(ast._Unparser):
        def fill(self, text=""):
            self.maybe_newline()
            self.write(indentation_string * self._indent + text)
    unparser = Builder() if obfuscate_indentation else ast._Unparser()
    return unparser.visit(ast_obj)
