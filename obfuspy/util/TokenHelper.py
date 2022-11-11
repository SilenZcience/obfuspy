import builtins
import tokenize
from types import BuiltinFunctionType

def getBuiltInMethods():
    builtin_function_names = [name for name, obj in vars(builtins).items() 
                          if isinstance(obj, BuiltinFunctionType) and not name.startswith("__")]
    return builtin_function_names