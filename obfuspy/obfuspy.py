#!/usr/bin/env python
# -*- coding: utf-8 -*-

from obfuspy.util.Chars import randChars_A
from obfuspy.util.FileHelper import accumulatePythonFiles
from obfuspy.util.ArgParser import parseArgs
from obfuspy.util.TokenHelper import getTokens, collectKeywords
from obfuspy.util.Generator import random_subset


class keyword_dicts:
    variable_dict = {}
    function_dict = {}
    classes_dict = {}
    builtin_dict = {}



def main():
    args = parseArgs()
    print("DEBUG: ARGS:", args)
    
    files = accumulatePythonFiles(getattr(args, 'PATH'))
    print("Found the following Python-files:\n", [x[0] for x in files])
    
    keywords = keyword_dicts()
    
    for file, target_name in files:
        try:
            fileToObfuscate = open(file, "r", encoding="utf-8").read()
        except:
            print(f"An Error occured opening the file {file}!")
            return
        tokens = getTokens(fileToObfuscate)
        collectKeywords(tokens, keywords)
    
if __name__ == '__main__':
    main()