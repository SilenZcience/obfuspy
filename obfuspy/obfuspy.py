

from obfuspy.util.Chars import randChars_A
from obfuspy.util.FileHelper import accumulatePythonFiles
from obfuspy.util.ArgParser import parseArgs
from obfuspy.util.TokenHelper import getBuiltInMethods
from obfuspy.util.Generator import random_subset






def main():
    args = parseArgs()
    print("DEBUG: ARGS:", args)
    
    files = accumulatePythonFiles(getattr(args, 'PATH'))
    print("Found the following Python-files:\n", [x[0] for x in files])
    
    keyword_dict = {}
    
    for file, target_name in files:
        try:
            fileToObfuscate = open(file, "r", encoding="utf-8").read()
        except:
            print(f"An Error occured opening the file {file}!")
            return
    
if __name__ == '__main__':
    main()