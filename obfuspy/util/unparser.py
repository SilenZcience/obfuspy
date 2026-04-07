
import ast

def unparse(ast_obj, indentation_string=' ' * 4):
    class Builder(ast._Unparser):
        def fill(self, text=''):
            self.maybe_newline()
            self.write(indentation_string * self._indent + text)
    return Builder().visit(ast_obj)
