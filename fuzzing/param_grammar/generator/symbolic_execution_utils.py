import re
from z3 import (
    Solver, Const, Real, Bool, SetSort, IntSort,
    String, StringVal, Implies, IsMember,
    Not, EmptySet, sat, And, Or, BoolVal
)

def parse_sexp(s):

    s = s.strip()
    # If the expression does not start with '(' then it's either a symbol or a value
    if not s.startswith('('):
        return s
    
    # Remove outer parentheses
    # e.g., "(and (>= x 0) (< x y))" -> "and (>= x 0) (< x y)"
    assert s[0] == '(' and s[-1] == ')', f"Expression does not have matching parentheses: {s}"
    inner = s[1:-1].strip()
    
    tokens = []
    bracket_level = 0
    current_token = []
    
    for char in inner:
        if char == '(':
            bracket_level += 1
            current_token.append(char)
        elif char == ')':
            bracket_level -= 1
            current_token.append(char)
        elif char.isspace() and bracket_level == 0:
            # Token delimiter
            if current_token:
                tokens.append("".join(current_token))
                current_token = []
        else:
            current_token.append(char)
    # Append last token if any
    if current_token:
        tokens.append("".join(current_token))
    
    # Now tokens[0] should be the operator, the rest are sub-expressions
    # For example, tokens = ["and", "(>= x 0)", "(< x y)"]
    operator = tokens[0]
    if len(tokens) == 1:
        # A single token could itself be an S-expression if it has parentheses
        return parse_sexp(operator)
    
    # Parse each subtoken (except the first which is operator)
    sub_exprs = []
    for t in tokens[1:]:
        sub_exprs.append(parse_sexp(t))
    
    return [operator] + sub_exprs


def build_z3_constraints(expr, var_map, solver, constraint_type):

    # If expr is a string (e.g. 'x', 'true', '5'), we treat it as a leaf node (variable or constant)
    if isinstance(expr, str):
        # It's not a constraint by itself; return None
        return None
    
    # Now expr is a list, e.g. ['and', [...], [...]]
    op = expr[0]

    # Handle top-level "assert" by just stripping it and building from the inside
    if op == 'assert':
        # There's exactly 1 sub-expression inside (assert ... )
        return build_z3_constraints(expr[1], var_map, solver, constraint_type)
    
    if op == 'and':
        # Combine all sub constraints with logical And
        sub_constraints = []
        for sub in expr[1:]:
            c = build_z3_constraints(sub, var_map, solver, constraint_type)
            if c is not None:
                sub_constraints.append(c)
        if sub_constraints:
            conj = And(*sub_constraints)
            solver.add(conj)
        return None
    
    if op == 'or':  # <--- NEW OR HANDLER
        # Combine all sub constraints with logical Or
        sub_constraints = []
        for sub in expr[1:]:
            c = build_z3_constraints(sub, var_map, solver, constraint_type)
            if c is not None:
                sub_constraints.append(c)
        if sub_constraints:
            disj = Or(*sub_constraints)
            solver.add(disj)
        return None
    
    if op == 'not':
        # There's exactly 1 sub-expression (not x)
        sub_expr = expr[1]
        # sub_expr might be a variable or a nested expression
        if isinstance(sub_expr, str):
            # sub_expr is a variable name
            return Not(var_map[sub_expr])
        else:
            # sub_expr is something else, e.g. (>= x 0)
            sc = build_z3_constraints(sub_expr, var_map, solver, constraint_type)
            if sc is not None:
                return Not(sc)
        return None
    
    # Otherwise, we might have something like (= x y), (>= x 0), (subset y x)
    # Typically, the structure is [op, left, right] or for 'subset': [op, A, B]
    if len(expr) == 3:
        left = expr[1]
        right = expr[2]
        
        # If left or right is itself a list (like (not x)), we recursively build that first
        z3_left = None
        if isinstance(left, list):
            z3_left = build_z3_constraints(left, var_map, solver, constraint_type)
        else:
            # It's a variable or constant
            if left in var_map:
                z3_left = var_map[left]
            else:
                # It might be something like 'true', 'false', or a numeric string
                z3_left = parse_constant(left, constraint_type)
        
        z3_right = None
        if isinstance(right, list):
            z3_right = build_z3_constraints(right, var_map, solver, constraint_type)
        else:
            if right in var_map:
                z3_right = var_map[right]
            else:
                z3_right = parse_constant(right, constraint_type)
        
        if op == '=':
            return z3_left == z3_right
        elif op == '!=':
            return z3_left != z3_right
        elif op == '>':
            return z3_left > z3_right
        elif op == '>=':
            return z3_left >= z3_right
        elif op == '<':
            return z3_left < z3_right
        elif op == '<=':
            return z3_left <= z3_right
        elif op == 'subset':
            # Use <= to represent subset
            # z3_left <= z3_right means: left is subset of right
            return z3_left <= z3_right
        elif op == '=>':
            # handle Implication
            return Implies(z3_left, z3_right)
        elif op == 'contains':
            # handle Membership
            # Check if the left operand is a member of the right set
            return IsMember(z3_left, z3_right)
        else:
            raise ValueError(f"Unknown operator '{op}'in {expr}.")
    else:
        raise ValueError(f"Unhandled expression structure: {expr}")


def parse_constant(val_str, constraint_type):
    val_str_l = val_str.lower()
    if constraint_type == 'boolean':
        if val_str_l == 'true':
            return BoolVal(True)
        elif val_str_l == 'false':
            return BoolVal(False)
        else:
            # Possibly an error or a variable name
            raise ValueError(f"Unexpected boolean constant: {val_str}")
    elif constraint_type == 'number':
        # Try to parse as int or float
        if '.' in val_str:
            return float(val_str)
        else:
            return int(val_str)
    elif constraint_type == 'array':
        # If we want to handle something like 'empty' => return an empty set
        if val_str_l == 'empty':
            return EmptySet(IntSort())
        # Otherwise, we don't handle direct set constants in this example
        raise ValueError(f"Unexpected array constant: {val_str}")
    else:
        # If it's just a string type or unknown, let's just return as-is
        return val_str


def solve_for_other_symbol(constraint_dict, known_symbol, known_value):
    constraint_str = constraint_dict.get("constraint", "")
    if not constraint_str:
        raise ValueError("No 'constraint' found in the provided dictionary.")
    
    constraint_type = constraint_dict.get("type", "").lower().strip()
    
    parsed_expr = parse_sexp(constraint_str)
    var_names = set()
    collect_variables(parsed_expr, var_names)
    
    if known_symbol not in var_names:
        # It's possible the expression references it in a sub form, but let's just check
        raise ValueError(f"Known symbol '{known_symbol}' not present in constraint.")
    
    solver = Solver()

    var_map = {}
    if constraint_type == 'number':
        for v in var_names:
            var_map[v] = Real(v)
    elif constraint_type == 'boolean':
        for v in var_names:
            var_map[v] = Bool(v)
    elif constraint_type == 'array':
        # We'll treat them as sets of integers
        # e.g. x => Set(IntSort())
        for v in var_names:
            var_map[v] = Const(v, SetSort(IntSort()))
    else:
        # We might handle strings or fallback here
        # For the original code, let's just assume if not number/boolean/array => string
        for v in var_names:
            # Because we only had example for string with '=' or '!='
            var_map[v] = String(v)
    
    if constraint_type == 'number':
        if isinstance(known_value, str):
            if '.' in known_value:
                known_value = float(known_value)
            else:
                known_value = int(known_value)
        solver.add(var_map[known_symbol] == known_value)
    elif constraint_type == 'boolean':
        if isinstance(known_value, str):
            known_value_lower = known_value.lower()
            if known_value_lower == 'true':
                known_value = True
            elif known_value_lower == 'false':
                known_value = False
            else:
                raise ValueError(f"Cannot interpret known_value '{known_value}' as boolean.")
        solver.add(var_map[known_symbol] == bool(known_value))
    elif constraint_type == 'array':
        # known_value should be a Python set (of ints) or something similar
        if not isinstance(known_value, set):
            # Try to parse it as well
            raise ValueError("For 'array' type, known_value must be a Python set of ints.")
        s_expr = EmptySet(IntSort())
        for elt in known_value:
            s_expr = s_expr.union(s_expr, s_expr.add(elt))
        solver.add(var_map[known_symbol] == s_expr)
    else:
        # String case
        from z3 import StringVal
        solver.add(var_map[known_symbol] == StringVal(str(known_value)))

    z3_constraint = build_z3_constraints(parsed_expr, var_map, solver, constraint_type)
    if z3_constraint is not None:
        solver.add(z3_constraint)
    
    if constraint_type == 'array':

        if '(subset ' in constraint_str.lower():

            subset_expressions = find_subset_expressions(parsed_expr)
            for sub_expr in subset_expressions:
                # sub_expr -> ['subset', 'y', 'x']
                if len(sub_expr) == 3:
                    left_side = sub_expr[1]
                    # If left_side is the unknown symbol and different from the known symbol, enforce non-empty
                    # Or if the known symbol is not 'y', meaning 'y' is unknown. 
                    if (isinstance(left_side, str) and left_side != known_symbol):
                        # left_side is the symbol we are solving for -> enforce var_map[left_side] != empty
                        solver.add(var_map[left_side] != EmptySet(IntSort()))
    

    result = solver.check()
    if result != sat:
        raise ValueError("No solution found for the given constraint.")
    
    model = solver.model()

    unknown_vars = var_names - {known_symbol}
    
    if len(unknown_vars) == 1:
        uv = unknown_vars.pop()
        return get_python_value(model[var_map[uv]], constraint_type)
    else:
        # Possibly return a dict for all unknown variables
        solution_dict = {}
        for uv in unknown_vars:
            solution_dict[uv] = get_python_value(model[var_map[uv]], constraint_type)
        return solution_dict


def collect_variables(expr, var_set):

    if isinstance(expr, str):
        # Check if it's an operator or a boolean constant
        if expr not in ('and', 'not', 'subset', 'assert',
                        '=', '!=', '>', '<', '>=', '<=', 
                        'true', 'false'):
            var_set.add(expr)
    else:
        # It's a list
        for sub in expr:
            collect_variables(sub, var_set)


def find_subset_expressions(expr):

    results = []
    if isinstance(expr, list):
        if len(expr) == 3 and expr[0] == 'subset':
            results.append(expr)
        else:
            for sub in expr:
                if isinstance(sub, list):
                    results.extend(find_subset_expressions(sub))
    return results


def get_python_value(z3_val, constraint_type):

    if z3_val is None:
        return None
    
    if constraint_type == 'number':
        if z3_val.is_int():
            return z3_val.as_long()
        elif z3_val.is_real():
            num = z3_val.numerator_as_long()
            den = z3_val.denominator_as_long()
            if den == 0:
                return float(num)
            else:
                return num / den
        else:
            return float(str(z3_val))
    elif constraint_type == 'boolean':
        return bool(z3_val)
    elif constraint_type == 'array':
        return str(z3_val)
    else:
        val_str = str(z3_val)
        if val_str.startswith('"') and val_str.endswith('"'):
            return val_str[1:-1]
        return val_str

if __name__ == "__main__":

    example_dict_and = {
        "constraint": "(and (>= x 0) (< x y))",
        "type": "number"
    }
    result_y = solve_for_other_symbol(example_dict_and, "x", 5)
    print("Numeric and-constraint => y:", result_y)  # Expect any y > 5

    example_dict_bool = {
        "constraint": "(= y (not x))",
        "type": "boolean"
    }
    result_bool = solve_for_other_symbol(example_dict_bool, "x", True)
    print("Boolean example => y:", result_bool)  # Expect False

    example_dict_subset = {
        "constraint": "(subset y x)",
        "type": "array"
    }
    result_subset = solve_for_other_symbol(example_dict_subset, "x", {1,2})
    print("Subset example => y:", result_subset)  # Expect some subset of {1,2} that is not empty

    example_dict_assert_bool = {
        "constraint": "(assert (= x true))",
        "type": "boolean"
    }

    try:
        result_assert = solve_for_other_symbol(example_dict_assert_bool, "x", True)
        print("Assert example => solution:", result_assert)
    except ValueError as e:
        print("Assert example => error:", e)
