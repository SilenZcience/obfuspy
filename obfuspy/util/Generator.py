
from itertools import product
# from random import shuffle

def random_subset(charList, length):
    for randomKeyword in product(charList, repeat=length):
        yield "".join(randomKeyword)