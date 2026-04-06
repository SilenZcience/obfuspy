

import builtins
from functools import lru_cache
import itertools
import json
import keyword
import random
import string
import subprocess
import sys


def _load_clean_builtins_default() -> set:
    code = (
        "import builtins, json;"
        "print(json.dumps(sorted(k for k in builtins.__dict__.keys() if not k.startswith('_'))))"
    )
    try:
        proc = subprocess.run(
            [sys.executable, '-I', '-S', '-c', code],
            capture_output=True,
            text=True,
            check=True,
        )
        return set(json.loads(proc.stdout))
    except Exception:
        # Fallback: best effort from current runtime if isolated subprocess is unavailable.
        return set(f for f in dir(builtins) if not f.startswith('_'))


BUILTINS_DEFAULT = _load_clean_builtins_default()
# `dir(builtins)` can be polluted at runtime (debuggers, sitecustomize, REPL tools).
# Keep only stable dunder builtins that are part of normal Python execution.
BUILTINS_DUNDER = {
    '__build_class__',
    '__import__',
}
KEYWORDS_VAL = {'True', 'False', 'None'}
UNSAFE_BUILTINS = {
    'super',
    '__build_class__',
    '__import__',
    'globals',
    'locals',
    'vars',
    'dir',
    'getattr',
    'setattr',
    'delattr',
    'hasattr',
    'eval',
    'exec',
    'compile',
    'type',
    'object',
    'isinstance',
    'issubclass',
    'property',
    'classmethod',
    'staticmethod',
    'True',
    'False',
    'None',
    'Ellipsis',
    'NotImplemented',
}
ALL_BUILTINS = BUILTINS_DEFAULT | BUILTINS_DUNDER | KEYWORDS_VAL - UNSAFE_BUILTINS
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
        # TODO: fix length usage, also duplicates allowed so limit to set length ONLY!
        lines = code.split('\n')
        for i, _ in enumerate(lines):
            if lines[i].strip():
                lines[i] += f"#{next(self.random_name_gen)}"
            else:
                lines[i] = f"#{random.choice(lines)}"
        return '\n'.join(lines)
