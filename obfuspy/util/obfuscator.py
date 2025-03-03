"""
obfuscator
"""

import ast
from obfuspy.util.charsets import CHARSETS
from obfuspy.util.randomizer import Randomizer
from obfuspy.util.unparser import unparse
from obfuspy.layers.layer_a import Layer_A
from obfuspy.layers.layer_b import Layer_B
from obfuspy.layers.layer_c import Layer_C
from obfuspy.layers.layer_d import Layer_D
from obfuspy.layers.layer_e import Layer_E
from obfuspy.layers.layer_f import Layer_F
from obfuspy.layers.layer_g import Layer_G


OBFUSCATE_NUMBERS = True
NUMERICAL_DENOMINATOR = 6
OBFUSCATE_STRINGS = True
OBFUSCATE_ASSIGNEMENTS = True
OBFUSCATE_ANNOTATIONS = True
OBFUSCATE_DOCSTRINGS = True

OBFUSCATE_VARIABLE_NAMES = False#
OBFUSCATE_ARGUMENT_NAMES = False#
OBFUSCATE_FUNCTION_NAMES = False#
OBFUSCATE_CLASS_NAMES = False#
VARIABLE_LENGTH = 5
VARIABLE_CHARSET = CHARSETS[0]

OBFUSCATE_IMPORTS = False#
OBFUSCATE_BUILTINS = False#

OBFUSCATE_ANTIDEBUG = False
ANTI_DEBUG_PROBABILITY = 0.2
OBFUSCATE_DEAD_CODE = False
DEAD_CODE_PROBABILITY = 1

OBFUSCATE_INDENTATION = False
INDENTATION_STRING = '\t\t\t'

OBFUSCATE_COMMENTS = False
COMMENT_LENGTH = 100
COMMENT_CHARSET = CHARSETS[0]


class Obfuscator:

    @staticmethod
    def obfuscate(file_modules: set) -> None:
        randomizer = Randomizer()
        randomizer.set_cmmt_data(COMMENT_LENGTH,  COMMENT_CHARSET )
        randomizer.set_name_data(VARIABLE_LENGTH, VARIABLE_CHARSET)

        layer_a = Layer_A(randomizer, NUMERICAL_DENOMINATOR)
        layer_b = Layer_B(randomizer)
        layer_c = Layer_C(randomizer)
        layer_d = Layer_D(randomizer)
        layer_e = Layer_E(randomizer)
        layer_f = Layer_F(randomizer, ANTI_DEBUG_PROBABILITY)
        layer_g = Layer_G(randomizer, DEAD_CODE_PROBABILITY)

        for file_module in file_modules:
        #     in_module  = os.path.splitext(os.path.basename(file_module.in_path))[0]
            # out_module = os.path.splitext(os.path.basename(file_module.out_path))[0]
            # visitor_a.file_map.add(in_module)
            file_module.set_tree(ast.parse(file_module.in_code))

            # for node in ast.walk(file_module.tree):
            #     if OBFUSCATE_VARIABLE_NAMES and isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            #         obfuscator.var_map.setdefault(node.id, next(Obfuscator.random_name_gen))
            #     elif OBFUSCATE_ARGUMENT_NAMES and isinstance(node, ast.arg):
            #         obfuscator.var_map.setdefault(node.arg, next(Obfuscator.random_name_gen))
            #     elif OBFUSCATE_FUNCTION_NAMES and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            #         obfuscator.var_map.setdefault(node.name, next(Obfuscator.random_name_gen))
            #     elif OBFUSCATE_CLASS_NAMES and isinstance(node, ast.ClassDef):
            #         obfuscator.var_map.setdefault(node.name, next(Obfuscator.random_name_gen))
            #     elif OBFUSCATE_IMPORTS and isinstance(node, ast.Import):
            #         obfuscator.var_map.setdefault(node.asname, next(Obfuscator.random_name_gen))
        # print(visitor_a.file_map)
        # print(obfuscator.var_map)


        # obfuscator.var_map.setdefault(Obfuscator.random_str_name, Obfuscator.random_str_name)
        # obfuscator.var_map.setdefault('s', next(Obfuscator.random_name_gen))
        # obfuscator.var_map.setdefault('c', next(Obfuscator.random_name_gen)) # the vars we use in the string deobfuscator
        # if OBFUSCATE_BUILTINS:
        #     for builtin in ALL_BUILTINS:
        #         obfuscator.var_map.setdefault(builtin, next(Obfuscator.random_name_gen))

        for file_module in file_modules:
            layer_g.visit(file_module.tree)
            out_code = unparse(file_module.tree, OBFUSCATE_INDENTATION, INDENTATION_STRING)
            if OBFUSCATE_COMMENTS:
                out_code = randomizer.generate_random_comments(out_code)
            prefix   = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n'
            post_fix = '\n# Obfuscated by *obfuspy* (Silas A. Kraume)\n'
            file_module.set_code(prefix + out_code + post_fix)
