import argparse


def parseArgs():
    parser = argparse.ArgumentParser(description='Obfuscate a python file/project.')

    parser.add_argument("PATH", action="store", default=None,
                        nargs="+", help="FILE(s) and/or FOLDER(s) to obfuscate")

    # parser.add_argument("-vl", "--variablelength", action="store", default=16,
    #                     type=int, nargs=1, help="set variable length")
    # parser.add_argument("-fl", "--functionlength", action="store", default=16,
    #                     type=int, nargs=1, help="set function length")
    # parser.add_argument("-cll", "--classlength", action="store", default=16,
    #                     type=int, nargs=1, help="set class length")
    # parser.add_argument("-cl", "--commentlength", action="store", default=16,
    #                     type=int, nargs=1, help="set comment length")

    # parser.add_argument("-nv", "--novariables", action="store_true", default=False,
    #                     help="do not obfuscate variable names")
    # parser.add_argument("-nf", "--nofunctions", action="store_true", default=False,
    #                     help="do not obfuscate function names")
    # parser.add_argument("-ncl", "--noclasses", action="store_true", default=False,
    #                     help="do not obfuscate class names")
    # parser.add_argument("-nn", "--nonumbers", action="store_true", default=False,
    #                     help="do not obfuscate numbers")
    # parser.add_argument("-ns", "--nostrings", action="store_true", default=False,
    #                     help="do not obfuscate strings")
    # parser.add_argument("-nc", "--nocomments", action="store_true", default=False,
    #                     help="do not add comments")

    return parser.parse_args()
