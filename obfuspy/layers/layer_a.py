import ast
import functools


class Layer_A(ast.NodeTransformer):
    """
    Layer A obfuscates numerical constants in the AST.
    """
    def __init__(self, _, numerical_denominator: int) -> None:
        self.numerical_denominator = numerical_denominator

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
                expr_str = '(1-1)'
            else:
                expr_str = self.deconstruct_number(node.value)
            return ast.parse(expr_str, mode='eval').body
        if isinstance(node.value, float):
            if node.value == 0:
                expr_str = '(1.0-1.0)'
            else:
                int_part = int(node.value)
                decimal_part = node.value - int_part
                if decimal_part == 0:
                    expr_str = self.deconstruct_number(int_part)
                else:
                    # Convert decimal to fraction (e.g., 0.5 -> 5/10)
                    decimal_str = str(decimal_part).split('.')[1]
                    numerator = int(decimal_str)
                    denominator = 10 ** len(decimal_str)
                    int_expr = self.deconstruct_number(int_part)
                    num_expr = self.deconstruct_number(numerator)
                    den_expr = self.deconstruct_number(denominator)
                    expr_str = f"({int_expr}+{num_expr}/{den_expr})"
            return ast.parse(expr_str, mode='eval').body
        return node
