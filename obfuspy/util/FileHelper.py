import os
from glob import iglob




def accumulatePythonFiles(paths):
    files = []
    for path in paths:
        p = os.path.realpath(path)
        if os.path.isfile(p):
            pathSplit = os.path.splitext(p)
            if pathSplit[1] == ".py":
                obfuscatedName = pathSplit[0] + "-obfuscated" + pathSplit[1]
                files.append((p, obfuscatedName))
        elif os.path.isdir(p):
            for element in iglob(p + '**/**/*.py', recursive=True):
                pathSplit = os.path.splitext(element)
                if pathSplit[1] == ".py":
                    obfuscatedName = pathSplit[0] + "-obfuscated" + pathSplit[1]
                    files.append((element, obfuscatedName))
    
    return files