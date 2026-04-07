import ast
import functools
import random


ZERO_EXPRESSIONS = [
    'int(all([[]]))',
    'int([] is [])',
    '(1%1)',
    '(~0+1)'
]
ZERO_LAMBDAS = [
    lambda n: f"({n}^{n})",
    lambda n: f"(0&{n})",
    lambda n: f"(1 << {n&63} >> {(n&63)+1})",
]
ONE_EXPRESSIONS = [
    'int(all([]))',
    '(~~1)',
    '(0^1^0)'
]
ONE_LAMBDAS = [
    lambda n: f"({n}//{n})",
    lambda n: f"({n}**0)",
    lambda n: f"(1 << {n&63} >> {n&63})"
]

class Layer_A(ast.NodeTransformer):
    """
    Layer A obfuscates numerical constants in the AST.
    """
    def __init__(self, _, __, numerical_denominator: str) -> None:
        self.numerical_denominator = int(numerical_denominator)

    @staticmethod
    def neg_inverse(s: str) -> str:
        if random.random() < 0.5:
            return f"-~({s}-1)"
        return f"~-({s}+1)"

    @staticmethod
    def zero_expr():
        if random.random() < 0.5:
            return random.choice(ZERO_EXPRESSIONS)
        return random.choice(ZERO_LAMBDAS)(random.randint(1, 999_999_999))

    @staticmethod
    def one_expr():
        if random.random() < 0.5:
            return random.choice(ONE_EXPRESSIONS)
        return random.choice(ONE_LAMBDAS)(random.randint(1, 999_999_999))

    @functools.lru_cache(maxsize=1_000)
    def deconstruct_number(self, num: int) -> str:
        r = ''
        if num > self.numerical_denominator:
            if num // self.numerical_denominator > 1:
                if num % self.numerical_denominator == 0:
                    r += f"({self.deconstruct_number(num // self.numerical_denominator)}*{self.numerical_denominator})"
                else:
                    r += f"({self.deconstruct_number(num // self.numerical_denominator)}*{self.numerical_denominator}+{num % self.numerical_denominator})"
            else:
                r += f"({self.numerical_denominator}+{self.deconstruct_number(num - self.numerical_denominator)})"
        else:
            r = f"{num}"
        return r

    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            if node.value == 0:
                expr_str = self.zero_expr()
            elif node.value == 1:
                expr_str = self.one_expr()
            else:
                expr_str = self.deconstruct_number(node.value)
            return ast.parse(self.neg_inverse(expr_str), mode='eval').body

        if isinstance(node.value, float):
            if node.value == 0:
                expr_str = self.zero_expr()
            elif node.value == 1:
                expr_str = self.one_expr()
            else:
                int_part = int(node.value)
                decimal_part = node.value - int_part
                if decimal_part == 0:
                    expr_str = self.deconstruct_number(int_part)
                    expr_str = self.neg_inverse(expr_str)
                else:
                    # Convert decimal to fraction (e.g., 0.5 -> 5/10)
                    decimal_str = str(decimal_part).split('.')[1]
                    numerator = int(decimal_str)
                    denominator = 10 ** len(decimal_str)
                    int_expr = self.deconstruct_number(int_part)
                    int_expr = self.neg_inverse(int_expr)
                    num_expr = self.deconstruct_number(numerator)
                    den_expr = self.deconstruct_number(denominator)
                    expr_str = f"({int_expr}+{num_expr}/{den_expr})"
            return ast.parse(f"({expr_str} * 1.0)", mode='eval').body
        return node
