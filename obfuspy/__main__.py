#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from obfuspy.arg_parser import parseArgs
from obfuspy.util.obfuscator import Obfuscator
from obfuspy.util.domain import File_Module


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
    args = parseArgs()
    # print("DEBUG: ARGS:", args)
    file_modules = acc_py_files(args.PATH)
    Obfuscator.obfuscate(file_modules)
    for file_module in file_modules:
        with open(file_module.out_path, 'w', encoding='utf-8') as f:
            f.write(file_module.out_code)

if __name__ == '__main__':
    main()
