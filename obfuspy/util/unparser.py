
import ast

def unparse(ast_obj, indentation_string=' ' * 4):
    try:
        unparser = ast._Unparser
    except (AttributeError, NameError):
        from _ast_unparse import Unparser as _Unparser
        unparser = _Unparser
    class Builder(unparser):
        def fill(self, text='', *, allow_semicolon=True):
            if hasattr(self, '_in_interactive') and hasattr(self, '_indent') and (
                self._in_interactive and not self._indent and allow_semicolon
            ):
                self.maybe_semicolon()
                self.write(text)
            else:
                self.maybe_newline()
                self.write(indentation_string * self._indent + text)
    return Builder().visit(ast_obj)
