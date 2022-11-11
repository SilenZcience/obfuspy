import builtins
import tokenize
from io import StringIO
from types import BuiltinFunctionType


def getBuiltInMethods():
    return [name for name, obj in vars(builtins).items()
                              if isinstance(obj, BuiltinFunctionType) and not name.startswith("__")]


def getTokens(inputFile):
    io_obj = StringIO(inputFile)
    return [list(a) for a in tokenize.generate_tokens(io_obj.readline)]


def collectKeywords(tokens, keywords):
    
    for i, x in enumerate(tokens[:-1]):
        print(i, x)
        print(tokens[i+1])
    # for toknum, tokval, start, end, line in tokens:

    return
