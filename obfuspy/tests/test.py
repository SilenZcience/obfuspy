


import io
import json
import random
import subprocess
from pathlib import Path

from obfuspy.__main__ import OBFUSCATION_LAYERS, acc_py_files, main
from obfuspy.util.charsets import CHARSETS


TESTFILES_DIR = Path(__file__).parent / 'testfiles'
TESTFILES_OBF_DIR = Path(__file__).parent / 'obfuscated' / 'testfiles'


def _layer_settings(layer_name: str, rng: random.Random) -> dict:
    if layer_name in {'Anti-Debug Statements', 'Anti-Tampering Statements', 'Dead Code'}:
        return {'probability': max(rng.random(), 0.15)}
    if layer_name == 'Numerical Constants':
        return {'numerical_denominator': rng.randint(2, 12)}
    return {}


def test_obfuspy():
    rng = random.Random()
    layer_names = list(OBFUSCATION_LAYERS)
    layer_count = rng.randint(len(layer_names)//2, len(layer_names)+5)
    selected_layers = rng.choices(layer_names, k=layer_count)

    json_file = io.StringIO(json.dumps({
        'layers': [{'name': layer_name, 'settings': _layer_settings(layer_name, rng)} for layer_name in selected_layers],
        'random_name_length': rng.randint(1, 32),
        'random_charset_index': rng.randint(0, len(CHARSETS) - 1),
        'random_comment_length': rng.randint(-1, 32),
        'indentation': '    ',
    }))

    file_modules = acc_py_files([TESTFILES_DIR])

    # json_file = io.StringIO(
    # )

    main(file_modules, json_file)

    for file_module in file_modules:
        plain_output = subprocess.run(['python', file_module.in_path], capture_output=True, text=True)
        obfuscated_output = subprocess.run(['python', file_module.out_path], capture_output=True, text=True)
        assert plain_output.returncode == 0, f"Execution failed for plain {file_module.in_path} with error: {plain_output.stderr}\n Used Layers: {json_file.getvalue()}"
        assert obfuscated_output.returncode == 0, f"Execution failed for obfuscated {file_module.out_path} with error: {obfuscated_output.stderr}\n Used Layers: {json_file.getvalue()}"
        assert plain_output.stdout == obfuscated_output.stdout, f"Output mismatch for {file_module.in_path} and {file_module.out_path}:\nPlain Output:\n{plain_output.stdout}\nObfuscated Output:\n{obfuscated_output.stdout}\n Used Layers: {json_file.getvalue()}"
