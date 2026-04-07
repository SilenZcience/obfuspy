#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import os
from obfuspy.gui import GUI
from obfuspy.util.domain import File_Module
from obfuspy.util.obfuscator import Obfuscator

from obfuspy.layers.layer_a import Layer_A
from obfuspy.layers.layer_b import Layer_B
from obfuspy.layers.layer_c import Layer_C
from obfuspy.layers.layer_d import Layer_D
from obfuspy.layers.layer_e import Layer_E
from obfuspy.layers.layer_f import Layer_F
from obfuspy.layers.layer_g import Layer_G
from obfuspy.layers.layer_h import Layer_H
from obfuspy.layers.layer_i import Layer_I
from obfuspy.layers.layer_j import Layer_J
from obfuspy.layers.layer_k import Layer_K
from obfuspy.layers.layer_l import Layer_L
from obfuspy.layers.layer_m import Layer_M
from obfuspy.layers.layer_n import Layer_N

OBFUSCATION_LAYERS = {
    'Numerical Constants':   Layer_A,
    'String Constants':      Layer_B,
    'Docstrings':            Layer_C,
    'Assignements':          Layer_D,
    'Annotations':           Layer_E,
    'Anti-Debug Statements': Layer_F,
    'Dead Code':             Layer_G,
    'Builtins':              Layer_H,
    'Imports':               Layer_I,
    'Arguments':             Layer_J,
    'Functions':             Layer_K,
    'Class Variables':       Layer_L,
    'Variables':             Layer_M,
    'Local Variables':       Layer_N,
}


def acc_py_files(arg_paths) -> set:
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
    file_modules = acc_py_files(parser.parse_args().PATH)
    # TODO: if no files? maybe GUI fileselectdialog
    settings: dict = GUI(OBFUSCATION_LAYERS).run()
    if settings is None:
        return
    settings['file_modules'] = file_modules
    settings['obf_layers'] = [(OBFUSCATION_LAYERS[l.name], l.settings.values()) for l in settings['layers']]
    # return
    Obfuscator.obfuscate(settings)
    for file_module in file_modules:
        with open(file_module.out_path, 'w', encoding='utf-8') as f:
            f.write(file_module.out_code)

if __name__ == '__main__':
    main()
