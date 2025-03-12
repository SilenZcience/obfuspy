

import builtins
from functools import lru_cache
import itertools
import keyword
import random
import string


BUILTINS_DEFAULT = set(f for f in dir(builtins) if not f.startswith('_'))
BUILTINS_DUNDER = set(f for f in dir(builtins) if f.startswith('_'))
# BUILTINS_DUNDER.update({
#     '__annotations__',
#     '__file__',
#     '__path__',
# })
KEYWORDS_VAL = {'True', 'False', 'None'}
ALL_BUILTINS = BUILTINS_DEFAULT | BUILTINS_DUNDER | KEYWORDS_VAL
ALL_KEYWORDS = set(keyword.kwlist + keyword.softkwlist)


class Randomizer:
    def __init__(self) -> None:
        self.random_name_gen = None
        self.random_str_name = 'deobfuscate_string'
        self.random_str_key  = random.randint(1_000, 999_999)

    def set_random_gen(self, n: int, char_set: list = None) -> None:
        self.random_name_gen = Randomizer.create_random_generator(n, char_set)

    def randomize_string(self) -> None:
        self.random_str_name = next(self.random_name_gen)
        self.random_str_key = random.randint(1_000, 999_999)


    @staticmethod
    @lru_cache(maxsize=None)
    def create_random_generator(n: int, char_set: list = None):
        return Randomizer._random_name_gen(n, char_set)

    @staticmethod
    def _random_name_gen(n: int, char_set: list = None):
        if char_set is None:
            char_set = string.ascii_letters
        buffer_size = 1_000

        def _name_gen(n: int):
            while True:
                name_gen = itertools.product(char_set, repeat=n)
                buffer = []
                for name in name_gen:
                    if len(buffer) == buffer_size:
                        yield buffer
                        buffer = []
                    s_name = ''.join(name)
                    if not s_name in ALL_KEYWORDS | ALL_BUILTINS:
                        buffer.append(s_name)
                yield buffer
                n += 1

        name_gen = _name_gen(n)

        while True:
            random_buffer = next(name_gen)
            random.shuffle(random_buffer)
            yield from random_buffer


    def generate_random_comments(self, code: str) -> str:
        lines = code.split('\n')
        for i, _ in enumerate(lines):
            if lines[i].strip():
                lines[i] += f"#{next(self.random_name_gen)}"
            else:
                lines[i] = f"#{random.choice(lines)}"
        return '\n'.join(lines)
