import argparse














def main():
    parser = argparse.ArgumentParser(description='Obfuscate a python file.')
    parser.add_argument("-nv", "--novariables", action="store_true", default=False,
                        help="do not obfuscate variable names")
    parser.add_argument("-nf", "--nofunctions", action="store_true", default=False,
                        help="do not obfuscate function names")
    parser.add_argument("-nn", "--nonumbers", action="store_true", default=False,
                        help="do not obfuscate numbers")
    parser.add_argument("-ns", "--nostrings", action="store_true", default=False,
                        help="do not obfuscate strings")
    
    args = parser.parse_args()
    print(args)
    
if __name__ == '__main__':
    main()