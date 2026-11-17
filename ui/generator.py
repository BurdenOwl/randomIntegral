import ast
import random
import sympy as sp  
import latexify
from sympy.integrals.risch import risch_integrate

x = sp.Symbol('x')
fraction = False
types = ["polynomial", "trigonometric", "exponential"]
terms = []

def make_random_piece(comp_type: str) -> str:
    if comp_type == "polynomial":
        power = random.randint(1, 4)
        coeff = random.randint(1, 9)
        return f"{coeff}*x**{power}"
    elif comp_type == "trigonometric":
        freq = random.randint(1, 3)
        return f"sin({freq}*x)"
    elif comp_type == "exponential":
        rate = random.randint(1, 2)
        return f"exp({rate}*x)"
    raise ValueError(f"Unsupported component type: {comp_type}")

def generate_and_differentiate(n) -> tuple[sp.Expr, sp.Expr]:
    global types
    global terms
    chosen_types = random.choices(types, weights=[0.5, 0.3, 0.2], k=random.randint(2, 6))
    terms = [make_random_piece(t) for t in chosen_types]
    if n:
        return terms
    operators = random.choices([" + ", " - ", " * "], k=len(terms) - 1)
    expr_str = terms[0] + "".join(
        operator + term for operator, term in zip(operators, terms[1:])
    )
    return expr_str


def generate_expression() -> sp.Expr:
    global fraction
    global terms
    global types
    if not fraction and random.randint(0, 3) == 1:
        fraction = True
        numerator = " + ".join(generate_and_differentiate(True))
        denominator = " + ".join(generate_and_differentiate(True))
        preexpression = f"({numerator}) / ({denominator})"
    else:
        preexpression = generate_and_differentiate(False)

    expression = sp.sympify(
        preexpression,
        locals={"x": x, "sin": sp.sin, "exp": sp.exp, "log": sp.log},
    )

    return expression


def generationFirst() -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    expression = generate_expression()
    derivative = sp.diff(expression, x)
    Risch_algorithm = risch_integrate(expression, x, rewrite_complex=True)

    return expression, derivative, Risch_algorithm



def expression_to_latex(expression: sp.Expr) -> str:
    expression_ast = ast.parse(str(expression), mode="eval").body
    return latexify.codegen.ExpressionCodegen(use_math_symbols=True).visit(expression_ast)