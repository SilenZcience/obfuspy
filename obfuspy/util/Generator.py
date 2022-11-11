from obfuspy.util.Chars import randChars_A

from itertools import product
from random import shuffle

def random_subset(charList, length):
    subset = ["".join(char) for char in [*product(charList, repeat=length)]]
    shuffle(subset)
    return subset