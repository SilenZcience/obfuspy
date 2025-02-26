#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from obfuspy.arg_parser import parseArgs
from obfuspy.util.obfuscator import Obfuscator
from obfuspy.util.domain import File_Module

def add_file(fileList: set, in_file: str) -> None:
    print("DEBUG:", in_file)
    if os.path.splitext(in_file)[1] in ['.py', '.py3', '.pyw', '.pyi']:
        fileList.add(File_Module(in_file))

def acc_py_files(arg_paths) -> set:
    file_modules = set()
    for path in arg_paths:
        if os.path.isfile(path):
            add_file(file_modules, path)
            continue
        for dirpath, _, files in os.walk(path):
            for in_file in files:
                add_file(file_modules, os.path.join(dirpath, in_file))
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
