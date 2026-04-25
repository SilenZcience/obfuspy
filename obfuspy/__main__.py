#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import os
from obfuspy.gui import GUI
from obfuspy.util.domain import File_Module
from obfuspy.util.obfuscator import Obfuscator

from obfuspy.layers.obfNumericalConstants import ObfNumericalConstants
from obfuspy.layers.obfStringConstants import ObfStringConstants
from obfuspy.layers.obfDocstrings import ObfDocStrings
from obfuspy.layers.obfAssignements import ObfAssignements
from obfuspy.layers.obfTypeAnnotations import ObfTypeAnnotations
from obfuspy.layers.obfAntiDebugging import ObfAntiDebugging
from obfuspy.layers.obfAntiTampering import ObfAntiTampering
from obfuspy.layers.obfDeadCode import ObfDeadCode
from obfuspy.layers.obfBuiltins import ObfBuiltins
from obfuspy.layers.obfImports import ObfImports
from obfuspy.layers.obfDefArguments import ObfDefArguments
from obfuspy.layers.obfDefNames import ObfDefnames
from obfuspy.layers.obfClassVariables import ObfClassVariables
from obfuspy.layers.obfModuleVariables import ObfModuleVariables
from obfuspy.layers.obfLocalVariables import ObfLocalVariables
from obfuspy.layers.obfClassNames import ObfClassNames

OBFUSCATION_LAYERS = {
    'Dead Code':                 ObfDeadCode,
    'Anti-Debug Statements':     ObfAntiDebugging,
    'Numerical Constants':       ObfNumericalConstants,
    'String Constants':          ObfStringConstants,
    'Docstrings':                ObfDocStrings,
    'Assignements':              ObfAssignements,
    'Type Annotations':          ObfTypeAnnotations,
    'Builtins':                  ObfBuiltins,
    'Function Arguments':        ObfDefArguments,
    'Function Names':            ObfDefnames,
    'Class Names':               ObfClassNames,
    'Local Variables':           ObfLocalVariables,
    'Class Variables':           ObfClassVariables,
    'Module Variables':          ObfModuleVariables,
    'Imports':                   ObfImports,
    'Anti-Tampering Statements': ObfAntiTampering,
}


def acc_py_files(arg_paths) -> set: # TODO: non python files should be copied to output folder without modification, maybe add option to ignore non python files
    file_modules = set()
    for path in arg_paths:
        if os.path.isfile(path):
            out_file = os.path.join(os.path.dirname(path), 'obfuscated', os.path.basename(path))
            split_ext = os.path.splitext(path)
            if split_ext[1] in ['.py', '.py3', '.pyw', '.pyi']:
                os.makedirs(os.path.dirname(out_file), exist_ok=True)
                file_modules.add(File_Module(path, out_file))
            continue
        if os.path.isdir(path):
            abs_path = os.path.abspath(path)
            parent_dir = os.path.dirname(abs_path)
            folder_name = os.path.basename(abs_path)
            for root, _, files in os.walk(path):
                for file in files:
                    in_file = os.path.join(root, file)
                    rel_path = os.path.relpath(in_file, path)
                    out_file = os.path.join(parent_dir, 'obfuscated', folder_name, rel_path)
                    split_ext = os.path.splitext(in_file)
                    if split_ext[1] in ['.py', '.py3', '.pyw', '.pyi']:
                        os.makedirs(os.path.dirname(out_file), exist_ok=True)
                        file_modules.add(File_Module(in_file, out_file))
    return file_modules

def main():
    parser = argparse.ArgumentParser(description='obfuscate a python file/module.')
    parser.add_argument('PATH', action='store', default=None,
                        nargs='+', help='FILE(s) and/or FOLDER(s) to obfuscate')
    parser.add_argument('--json', action='store', help='Path to JSON file to load settings from (overrides GUI)',
                        default=None)

    file_modules = acc_py_files(parser.parse_args().PATH)
    json_settings_path = parser.parse_args().json

    gui = GUI(OBFUSCATION_LAYERS)
    if json_settings_path:
        settings = gui.load_settings_from_json(json_settings_path)
        if settings is None:
            return
    else:
         # TODO: if no files? maybe GUI fileselectdialog
        settings: dict = gui.run() # TODO: autosave latest config
        if settings is None:
            return

    settings['obf_layers'] = [(OBFUSCATION_LAYERS[l.name], l.settings.values()) for l in settings['layers']]
    settings['file_modules'] = file_modules

    Obfuscator.obfuscate(settings)
    for file_module in file_modules:
        print(f'Writing {file_module.out_path}...')
        with open(file_module.out_path, 'w', encoding='utf-8') as f:
            f.write(file_module.out_code)

if __name__ == '__main__':
    main()
