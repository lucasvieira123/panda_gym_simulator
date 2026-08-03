# %%
from typing_extensions import Literal
from pyparsing import Dict, ParseResults, Word, alphas, nums, oneOf, infixNotation, opAssoc, ParserElement
from typing import List, Optional, Union, Tuple, Dict
import re

from sympy import  sympify, to_dnf

from expression.conditional_expression import ConditionalExpression
from scenario.scenario import Scenario
from logger import trace, setup_logger
from pyparsing import pyparsing_common as ppc
from pyparsing import Regex


# %%
def _configure_conditional_expression_parsing() -> ParserElement:
    """
    Configures and returns a parser for logical and relational expressions.

    This function creates a parsing grammar using the `pyparsing` library, supporting:
        - Identifiers (variable names): letters, digits, and underscores.
        - Numeric values.
        - Relational operators: <=, >=, <, >, ==, !=
        - Logical operators: AND, OR
        - Parentheses for grouping and nested expressions.
        - Operator precedence and associativity via infix notation.

    The returned grammar can be used to parse conditional expression strings commonly used
    in scenarios or rule-based systems.

    Parameters
    ----------
    None

    Returns
    -------
    ParserElement
        A parsing object configured to handle logical and comparison expressions with nested structures.

    Examples
    --------
    >>> parser = _configure_conditional_expression_parsing()
    >>> result = parser.parseString("a > 10 AND (b <= 20 OR c != 5)")
    >>> print(result.asList())
    ['a', '>', '10', 'AND', ['b', '<=', '20', 'OR', 'c', '!=', '5']]

    Raises
    ------
    pyparsing.ParseException
        If the input string does not conform to the supported grammar.
    """
        
    # Configure pyparsing to ignore whitespace
    ParserElement.enablePackrat()

    # Define basic expression elements
    identifier = Word(alphas, alphas + nums + "_")
    #suporta a números inteiros
    # number = Word(nums)

    # Suporte a números inteiros, floats, negativos, notação científica:
    number = Regex(r"-?\d+(\.\d+)?([eE][+-]?\d+)?")

    # Define comparison operators
    relational_operator = oneOf("<= >= < > == !=")

    # Define operands
    operand = identifier | number

    # Define logical expressions with operator precedence
    parse_settings = infixNotation(operand,
        [
            (relational_operator, 2, opAssoc.LEFT),
            ("AND", 2, opAssoc.LEFT),
            ("OR", 2, opAssoc.LEFT),
        ])

    return parse_settings

_CONDITIONAL_EXPRESSION_PARSER = _configure_conditional_expression_parsing()
# %%
@trace
def _extract_relational_expressions(conditional_expression_str: str) -> List[str]:
    """
    Recursively extracts atomic (leaf) relational expressions from a conditional expression string.

    This function parses a conditional expression string and traverses the resulting parse tree,
    collecting only simple relational conditions (e.g., "a > 10", "b <= 20"). Logical operators
    (AND, OR) and nested groupings are ignored; recursion continues until all atomic relations
    are found.

    Parameters
    ----------
    conditional_expression_str : str
        The input conditional/logical expression string to be parsed.

    Returns
    -------
    list of str
        A list of all atomic relational expressions found, each as a string in the form
        "<identifier> <operator> <value>".

    Examples
    --------
    >>> _extract_relational_expressions("a > 10 AND (b <= 20 OR c != 5)")
    ['a > 10', 'b <= 20', 'c != 5']
    >>> _extract_relational_expressions("(x != 10) OR (y >= 5 AND z < 100)")
    ['x != 10', 'y >= 5', 'z < 100']

    Raises
    ------
    pyparsing.ParseException
        If the input string cannot be parsed as a conditional expression.
    """
    def extract_leaves(parsed_conditional_expr_list: Union[str, List]) -> List[str]:
        if isinstance(parsed_conditional_expr_list, str):
            return []
        elif len(parsed_conditional_expr_list) == 3 and parsed_conditional_expr_list[1] in ["<=", ">=", "<", ">", "==", "!="]:
            return [" ".join(parsed_conditional_expr_list)]
        else:
            leaves: List[str] = []
            for sub_expr in parsed_conditional_expr_list:
                leaves.extend(extract_leaves(sub_expr))
            return leaves

    parse_settings: ParserElement = _CONDITIONAL_EXPRESSION_PARSER
    parsed_conditional_expression: ParseResults = parse_settings.parseString(conditional_expression_str, parseAll=True)

    parsed_conditional_expr_list=parsed_conditional_expression.asList()

    extracted_leaves=extract_leaves(parsed_conditional_expr_list)

    return extracted_leaves

# %%
@trace
def _relational_expressions_to_key_dict(relational_expressions: list[str]) -> dict[str, str]:
    """
    Converts a list of relational expressions into a dictionary with indexed keys ("x1", "x2", ...).

    Each relational expression in the input list is assigned a key of the form "xN", where N
    is its (1-based) position in the list. The resulting dictionary maps each key to its corresponding
    relational expression.

    Parameters
    ----------
    relational_expressions : list of str
        List of relational expressions as strings.

    Returns
    -------
    dict of str to str
        Dictionary where keys are 'x1', 'x2', ..., 'xn' and values are the corresponding
        relational expressions from the input list.

    Examples
    --------
    >>> _relational_expressions_to_key_dict(["a > 10", "b <= 20", "c != 5"])
    {'x1': 'a > 10', 'x2': 'b <= 20', 'x3': 'c != 5'}
    >>> _relational_expressions_to_key_dict([])
    {}
    """
    map_key = {f"x{i+1}": expr for i, expr in enumerate(relational_expressions)}

    return map_key

# %%
@trace
def _replace_relational_expression_to_keys(relational_expression_str: str, map_key:dict) -> str:
    """
    Replace occurrences of dictionary values with their corresponding keys in a relational expression string.

    For each (key, value) pair in `map_key`, every occurrence of `value` in the input string is replaced
    by `key`. This is typically used to map full relational expressions (e.g., "a > 10") to symbolic
    variables (e.g., "x1") within a logical expression.

    Parameters
    ----------
    relational_expression_str : str
        The relational expression string in which replacements will be performed.
    map_key : dict of str to str
        Dictionary mapping keys (e.g., 'x1', 'x2') to their corresponding relational expressions (e.g., 'a > 10').
        Each value found in the input string will be replaced by its associated key.

    Returns
    -------
    str
        The updated relational expression string with values replaced by keys.

    Examples
    --------
    >>> mapping = {'x1': 'a > 10', 'x2': 'b <= 20'}
    >>> _replace_relational_expression_to_keys("if (a > 10 AND b <= 20)", mapping)
    'if (x1 AND x2)'
    """
    for key, value in map_key.items():
        relational_expression_str = relational_expression_str.replace(value, key)
    return relational_expression_str

# %%
@trace
def _replace_logical_operators(conditional_expression_str: str, scenario_operators: bool = False) -> str:
    """
    Replace logical operators in a conditional expression string.

    By default, replaces textual logical operators ('AND', 'OR') with their symbolic
    equivalents ('&', '|'). If `scenario_operators` is True, performs the reverse
    replacement: symbolic operators ('&', '|') are replaced with their textual forms.

    Parameters
    ----------
    conditional_expression_str : str
        The conditional expression string where replacements will be performed.
    scenario_operators : bool, optional
        If True, replace '&' with 'AND' and '|' with 'OR'.
        If False (default), replace 'AND' with '&' and 'OR' with '|'.

    Returns
    -------
    str
        The updated conditional expression string with logical operators replaced.

    Examples
    --------
    >>> _replace_logical_operators("a > 10 AND b <= 20")
    'a > 10 & b <= 20'

    >>> _replace_logical_operators("a > 10 & b <= 20", scenario_operators=True)
    'a > 10 AND b <= 20'
    """
    if scenario_operators:
        return conditional_expression_str.replace('&', 'AND').replace('|', 'OR')
    else:
        return conditional_expression_str.replace('AND', '&').replace('OR', '|')

# %%
@trace
def _transform_conditional_expression_to_symbolic(conditional_expression_str: str) -> tuple[str, dict[str, str]]:
    """
    Transform a conditional expression string into a symbolic, indexed form.

    The transformation applies the following pipeline:
      1. Parse the input expression using the pyparsing grammar.
      2. Extract all leaf relational expressions (e.g., "a <= 3", "b > 10").
      3. Map each relational expression to an indexed key: x1, x2, ..., xn.
      4. Replace each relational expression in the original string with its key.
      5. Replace logical operators 'AND'/'OR' with '&'/'|'.

    Parameters
    ----------
    conditional_expression_str : str
        The original conditional expression string. Example:
        "(((a <= 3 AND (b > 10 OR c == 10)) OR ((d != 5 AND e >= 20) OR f < 2)) AND ((g <= 7 OR h > 8) AND (i == 9 OR j != 3)))"

    Returns
    -------
    tuple of (str, dict of str to str)
        symbolic_conditional_expression_str : str
            The normalized/symbolic conditional expression, e.g.,
            "(((x1 & (x2 | x3)) | ((x4 & x5) | x6)) & ((x7 | x8) & (x9 | x10)))"
        map_relational_expression_to_key_dict : dict of str to str
            A mapping from keys ('x1', ...) to original relational expressions, e.g.,
            {"x1": "a <= 3", "x2": "b > 10", ...}

    Raises
    ------
    pyparsing.ParseException
        If the input string cannot be parsed by the configured grammar.

    Notes
    -----
    Keys are assigned in the order relational expressions appear in the input.
    Logical operator mapping: AND -> '&', OR -> '|'.

    Examples
    --------
    >>> expr = "a > 5 AND b <= 7 OR c != 3"
    >>> symbolic_expr, key_map = _transform_conditional_expression_to_symbolic(expr)
    >>> print(symbolic_expr)
    '(x1 & x2) | x3'
    >>> print(key_map)
    {'x1': 'a > 5', 'x2': 'b <= 7', 'x3': 'c != 3'}
    """
    
    relational_expressions_list: List[str] = _extract_relational_expressions(conditional_expression_str)

    map_relational_expression_to_key_dict: Dict[str, str] = (
        _relational_expressions_to_key_dict(relational_expressions_list)
    )

    conditional_expression_str = _replace_relational_expression_to_keys(conditional_expression_str, map_relational_expression_to_key_dict)
    conditional_expression_str = _replace_logical_operators(conditional_expression_str)

    symbolic_expression_str = conditional_expression_str
    return symbolic_expression_str, map_relational_expression_to_key_dict

# %%
@trace
def _symbolic_conditional_to_dnf(symbolic_conditional_expression_str: str) -> str:
    """
    Convert a symbolic conditional expression into Disjunctive Normal Form (DNF).

    Uses `sympy.sympify` to parse the symbolic expression and `sympy.to_dnf` to
    convert it to its equivalent DNF (Disjunctive Normal Form).

    Parameters
    ----------
    symbolic_conditional_expression_str : str
        The input conditional expression in string format, using only symbolic variable
        keys (e.g., 'x1', 'x2', ...) and symbolic logical operators:
        - '&' for AND
        - '|' for OR
        - '~' for NOT (if used)

        Example:
            "((x1 & (x2 | x3)) | x4)"

    Returns
    -------
    str
        The DNF-equivalent conditional expression as a string.

    Examples
    --------
    >>> _symbolic_conditional_to_dnf("(x1 & (x2 | x3)) | x4")
    '(x1 & x2) | (x1 & x3) | x4'

    Notes
    -----
    - Uses `simplify=True` to reduce the result if possible.
    - Uses `force=True` to allow conversion even if the input is not strictly Boolean.
    """
    simplified_conditional_expression = sympify(symbolic_conditional_expression_str)
    dnf_cond_expr = to_dnf(simplified_conditional_expression, simplify=True, force=True)
    return str(dnf_cond_expr)

# %%
@trace
def _revert_keys_to_relational_expressions(
    dnf_cond_expr: str, 
    map_relational_expression_to_key_dict: dict[str, str]
) -> str:
    """
    Replace indexed keys (e.g., 'x1', 'x2', ...) with their original relational
    expressions in a (usually DNF) conditional expression string.

    Parameters
    ----------
    dnf_cond_expr : str
        The conditional expression string (often in DNF) that contains keys.
        For example: '(x1 & x2) | x3'
    map_relational_expression_to_key_dict : dict of str to str
        Dictionary mapping each key to its original relational expression.
        Example: {'x1': 'a <= 3', 'x2': 'b > 10', 'x3': 'c != 5'}

    Returns
    -------
    str
        The conditional expression string with all keys replaced by their original
        relational expressions.

    Examples
    --------
    >>> mapping = {'x1': 'a <= 3', 'x2': 'b > 10', 'x3': 'c != 5'}
    >>> _revert_keys_to_relational_expressions("(x1 & x2) | x3", mapping)
    '(a <= 3 & b > 10) | c != 5'

    Notes
    -----
    - If a key occurs multiple times, all occurrences are replaced.
    - This does a simple string replacement, so ambiguous key names may cause
      unexpected results if keys are not unique or are substrings of each other.
    """
    for key, value in map_relational_expression_to_key_dict.items():
        dnf_cond_expr = dnf_cond_expr.replace(key, value)
    return dnf_cond_expr

# %%
@trace
def _revert_logical_operators(dnf_cond_expr: str) -> str:
    """
    Replace symbolic logical operators ('&', '|') with textual equivalents
    ('AND', 'OR') in a conditional expression string.

    Parameters
    ----------
    dnf_cond_expr : str
        Conditional expression string (typically in DNF form) containing
        symbolic logical operators '&' (AND) and '|' (OR).

    Returns
    -------
    str
        The conditional expression string with '&' replaced by 'AND'
        and '|' replaced by 'OR'.

    Examples
    --------
    >>> _revert_logical_operators("(x1 & x2) | x3")
    '(x1 AND x2) OR x3'

    Notes
    -----
    - Uses `_replace_logical_operators` helper for conversion.
    - Does a direct string replacement: nested or redundant spaces are preserved.
    """
    dnf_cond_expr= _replace_logical_operators(dnf_cond_expr, scenario_operators=True)
    return dnf_cond_expr

# %%
@trace
def conditional_expression_to_dnf(
    conditional_expression_str: str,
    *,
    output_operators: Literal["text", "symbolic"] = "text",
    return_mapping: bool = False,
):
    """
    Convert a raw conditional expression to Disjunctive Normal Form (DNF).

    This function parses a logical/relational expression, extracts all atomic
    conditions, normalizes them with symbolic keys (x1, x2, ...), rewrites the
    logic using symbolic operators (&, |), applies the DNF transformation, and
    optionally restores human-readable expressions and operators.

    The pipeline consists of:
        1. Parse the expression and extract atomic relational conditions.
        2. Replace conditions by symbolic keys (x1, x2, ...) and logical operators
           AND/OR by &/| (symbolic form).
        3. Transform the expression to Disjunctive Normal Form (DNF).
        4. Optionally, revert keys and operators to original human-readable form.

    Parameters
    ----------
    conditional_expression_str : str
        The original conditional expression, e.g.,
        "((a <= 3 AND (b > 10 OR c == 10)) OR ((d != 5 AND e >= 20) OR f < 2))".
    output_operators : {"text", "symbolic"}, default "text"
        Output format for logical operators:
        - "text": Returns AND/OR (human-readable).
        - "symbolic": Returns &/| (symbolic form).
    return_mapping : bool, default False
        If True, returns a tuple with the DNF string and the mapping from keys (x1, x2, ...)
        to the original relational expressions.

    Returns
    -------
    str or tuple of (str, dict[str, str])
        If return_mapping is False: returns the DNF expression as a string.
        If return_mapping is True: returns (dnf_str, mapping_dict).

    Raises
    ------
    pyparsing.ParseException
        If the input expression cannot be parsed.

    Notes
    -----
    - Relational expressions are mapped in the order they appear.
    - Supported logical operator mapping:
        AND -> &
        OR  -> |
        ~   -> NOT (if applicable)

    Examples
    --------
    >>> conditional_expression_to_dnf("a >= 3 AND (b < 10 OR c != 5)")
    'a >= 3 AND b < 10 OR a >= 3 AND c != 5'

    >>> conditional_expression_to_dnf("a >= 3 AND (b < 10 OR c != 5)", output_operators="symbolic")
    '(a >= 3 & b < 10) | (a >= 3 & c != 5)'

    >>> dnf_str, mapping = conditional_expression_to_dnf(
    ...     "((x <= 2 OR y > 7) AND (z != 5 OR w == 1))",
    ...     return_mapping=True
    ... )
    >>> print(dnf_str)
    '((x <= 2 AND z != 5) OR (x <= 2 AND w == 1) OR (y > 7 AND z != 5) OR (y > 7 AND w == 1))'
    >>> print(mapping)
    {'x1': 'x <= 2', 'x2': 'y > 7', 'x3': 'z != 5', 'x4': 'w == 1'}
    """
 
    # 1) Transform into symbolic expression (&, |) + mapping
    symbolic_conditional_expression_str, map_relational_expression_to_key_dict = _transform_conditional_expression_to_symbolic(conditional_expression_str)

    # 2) Convert to DNF in symbolic form
    dnf_symbolic_conditional_str = _symbolic_conditional_to_dnf(symbolic_conditional_expression_str)

    # 3) Replace keys with original conditions
    dnf_conditional_expr_with_relational_expr = _revert_keys_to_relational_expressions(
        dnf_symbolic_conditional_str, map_relational_expression_to_key_dict
    )

    # 4) Adjust operators depending on output format
    if output_operators == "text":
        final_dnf_conditional_exp_str = _revert_logical_operators(dnf_conditional_expr_with_relational_expr)  # &/| -> AND/OR
    else:
        final_dnf_conditional_exp_str = dnf_conditional_expr_with_relational_expr  # keep &/|

    if return_mapping:
        return final_dnf_conditional_exp_str, map_relational_expression_to_key_dict
    return final_dnf_conditional_exp_str

# %%
@trace
def _decompose_relational_expression(relational_expression: str) -> Tuple[str, str, str]:
    """
    Parse a relational expression string into its variable, operator, and value components.

    Parameters
    ----------
    relational_expression : str
        The relational expression to parse, in the form "<variable> <operator> <value>".
        Examples: "a >= 3", "temperature < 22", "b != 7"

    Returns
    -------
    tuple of str
        A tuple containing (variable, operator, value), where:
            variable : str
                The name of the variable.
            operator : str
                The relational operator (one of '>=', '<=', '>', '<', '==', '!=').
            value : str
                The value as a string (can be further converted to int/float if needed).

    Raises
    ------
    ValueError
        If the expression is not in a recognized relational format.

    Examples
    --------
    >>> _decompose_relational_expression("a >= 3")
    ('a', '>=', '3')

    >>> _decompose_relational_expression("temperature < 22")
    ('temperature', '<', '22')

    >>> _decompose_relational_expression("b != 7")
    ('b', '!=', '7')
    """
    match = re.match(r"(\w+)\s*(>=|<=|>|<|==|!=)\s*(.+)", relational_expression)
    if match:
        variable, operator, value = match.groups()
        return variable, operator, value
    else:
        raise ValueError(f"Invalid expression format: {relational_expression}")

# %%
@trace
def _get_relational_expression_region(
    var_name: str,
    operator: str,
    value: Union[int, float],
    min_val: float,
    max_val: float,
    type_val: str 
) -> Union[Tuple[float, float], List[Tuple[float, float]]]:
    """
    Compute the numeric region(s) within [min_val, max_val] that satisfy
    a given relational expression.

    This function interprets a relational condition of the form
    "<var_name> <operator> <value>" and maps it to the region(s) of values,
    within the closed interval [min_val, max_val], where the expression holds.
    For inequality ('!='), returns two disjoint intervals.

    Parameters
    ----------
    var_name : str
        The variable name in the relational expression (not used in the computation, but included for clarity).
    operator : str
        The comparison operator. Supported operators: '>=', '<=', '>', '<', '==', '!='.
    value : int, float or str
        The right-hand side value of the relational expression. Will be cast to float.
    min_val : float
        Minimum possible value of the variable (inclusive).
    max_val : float
        Maximum possible value of the variable (inclusive).

    Returns
    -------
    tuple of float
        A single interval as (low, high) for relational operators that define a contiguous region.
    list of tuple of float
        A list of two intervals [(low1, high1), (low2, high2)] for the '!=' operator (two disjoint regions).

    Raises
    ------
    ValueError
        If the operator is not supported.

    Examples
    --------
    >>> _get_relational_expression_region("a", ">=", 3, 0, 10)
    (3.0, 10.0)

    >>> _get_relational_expression_region("b", "<", 5, 0, 10)
    (0.0, 4.999999999)

    >>> _get_relational_expression_region("c", "!=", 7, 0, 10)
    [(0.0, 6.999999999), (7.000000001, 10.0)]

    Notes
    -----
    - For strict inequalities ('>' and '<'), a small epsilon (1e-9) is added/subtracted to exclude the boundary.
    - For the '!=' operator, returns two non-overlapping intervals excluding the given value.
    - The function assumes all values are within [min_val, max_val].
    """
    
    if type_val == 'int':
        value = int(value)
        offset = 1
    elif type_val == 'float':
        value = float(value)
        offset = 1e-9

    

    if operator == '>=':
        return (value, max_val)
    elif operator == '<=':
        return (min_val, value)
    elif operator == '>':
        return (value + offset, max_val)  # Adding a small value to make it exclusive
    elif operator == '<':
        return (min_val, value - offset) # Subtracting a small value to make it exclusive
    elif operator == '==':
        return (value, value)
    elif operator == '!=':
        return [(min_val, value - offset), (value + offset, max_val)]
    else:
        raise ValueError(f"Unsupported operator: {operator}")

# %%
@trace
def _calculate_jaccard_similarity(
    relational_expression_1: str,
    relational_expression_2: str,
    monitored_parameters_dict: dict,
) -> float:
    """
    Calculate the Jaccard similarity between two relational expressions over monitored variable ranges.

    Given two relational expressions (e.g., "temperature >= 30"), this function decomposes them,
    computes their respective value regions, and evaluates their similarity via the Jaccard index:

        Jaccard(A, B) = |A ∩ B| / |A ∪ B|

    Handles special cases for equality (==) and inequality (!=) operators, including
    proper treatment of disjoint intervals for '!='.

    Parameters
    ----------
    relational_expression_1 : str
        First relational expression, formatted as "<variable> <operator> <value>" (e.g., "a >= 3").
    relational_expression_2 : str
        Second relational expression, with the same format.
    monitored_parameters_dict : dict
        Metadata about the variables and their value ranges.
        Example:
        {
            "a": {"min_value": 0, "max_value": 10, "type": "int"},
            "b": {"min_value": 0, "max_value": 100, "type": "float"},
            ...
        }

    Returns
    -------
    float
        Jaccard similarity in [0.0, 1.0]. Returns 0.0 if variables differ or intervals do not overlap.
        - 1.0: Complete overlap
        - 0.0: No overlap

    Raises
    ------
    ValueError
        If an expression cannot be parsed or contains unsupported operators.

    Notes
    -----
    - If the expressions refer to different variables, returns 0.0.
    - Supports operators: <=, >=, <, >, ==, !=.
    - For '!=', the range is split into two disjoint intervals.
    - Overlap between equality and other intervals is considered as a single point.
    - Uses small epsilon for strict inequalities to avoid boundary overlap.

    Examples
    --------
    >>> monitored_params = {
    ...     "a": {"min_value": 0, "max_value": 10, "type": "int"}
    ... }
    >>> _calculate_jaccard_similarity("a >= 3", "a <= 7", monitored_params)
    0.57143
    >>> _calculate_jaccard_similarity("a == 5", "a != 5", monitored_params)
    0.0
    >>> _calculate_jaccard_similarity("a == 5", "a >= 0", monitored_params)
    0.1
    """

    try:
        var1, op1, val1 = _decompose_relational_expression(relational_expression_1)
        var2, op2, val2 = _decompose_relational_expression(relational_expression_2)
    except ValueError as e:
        print(e)
        return 0.0

    # Ensure the variable names are the same
    if var1 != var2:
        return 0.0

    # Get variable ranges
    var_info = monitored_parameters_dict.get(var1)
    if not var_info:
        print(f"Variable {var1} not found in ranges.")
        return 0.0

    min_val = var_info['min_value']
    max_val = var_info['max_value']
    type_val = var_info['type']

    # Get ranges for each expression
    region1 = _get_relational_expression_region(var1, op1, val1, min_val, max_val, type_val)
    region2 = _get_relational_expression_region(var2, op2, val2, min_val, max_val, type_val)

    def compute_region_intersection_union(region1, region2):
        """
        Helper function to calculate intersection and union of two ranges.
        """
        if isinstance(region1, list):
            intersections = []
            for r1 in region1:
                if isinstance(region2, list):
                    for r2 in region2:
                        intersections.append((max(r1[0], r2[0]), min(r1[1], r2[1])))
                else:
                    intersections.append((max(r1[0], region2[0]), min(r1[1], region2[1])))
        else:
            if isinstance(region2, list):
                intersections = [(max(region1[0], r2[0]), min(region1[1], r2[1])) for r2 in region2]
            else:
                intersections = [(max(region1[0], region2[0]), min(region1[1], region2[1]))]
        
        valid_intersections = [r for r in intersections if r[0] <= r[1]]
        intersection_length = sum(r[1] - r[0] for r in valid_intersections)
        
        union_min = min(region1[0] if not isinstance(region1, list) else min(r[0] for r in region1),
                        region2[0] if not isinstance(region2, list) else min(r[0] for r in region2))
        union_max = max(region1[1] if not isinstance(region1, list) else max(r[1] for r in region1),
                        region2[1] if not isinstance(region2, list) else max(r[1] for r in region2))
        union_length = union_max - union_min
        
        return intersection_length, union_length

    # Calculate intersection and union considering the equality operator cases
    if op1 == '==' and op2 != '==':
        if isinstance(region2, list):
            region2_min, region2_max = min(region2[0][0], region2[1][0]), max(region2[0][1], region2[1][1])
            if region2_min <= region1[0] <= region2_max:
                intersection_length = 1
                union_length = region2_max - region2_min
            else:
                return 0.0
        else:
            if region2[0] <= region1[0] <= region2[1]:
                intersection_length = 1
                union_length = region2[1] - region2[0]
            else:
                return 0.0
    elif op2 == '==' and op1 != '==':
        if isinstance(region1, list):
            region1_min, region1_max = min(region1[0][0], region1[1][0]), max(region1[0][1], region1[1][1])
            if region1_min <= region2[0] <= region1_max:
                intersection_length = 1
                union_length = region1_max - region1_min
            else:
                return 0.0
        else:
            if region1[0] <= region2[0] <= region1[1]:
                intersection_length = 1
                union_length = region1[1] - region1[0]
            else:
                return 0.0
    elif op1 == '==' and op2 == '==':
        if val1 == val2:
            return 1.0
        else:
            return 0.0
    else:
        intersection_length, union_length = compute_region_intersection_union(region1, region2)

    # Calculate the Jaccard similarity
    if union_length == 0:
        return 0.0
    similarity = intersection_length / union_length
    return round(similarity,5)

# %%
@trace
def pair_relational_expressions(relational_expression_1: str,
                                relational_expression_2: str) -> str:
    """
    Pair relational expressions from two conditional expressions by variable name.

    This function extracts all atomic relational expressions (leaves) from
    each conditional expression string and matches those with the same variable name,
    returning a list of tuples (pairing the corresponding expressions from both).

    Parameters
    ----------
    relational_expression_1 : str
        First conditional expression as a string.
    relational_expression_2 : str
        Second conditional expression as a string.

    Returns
    -------
    list of tuple of str
        List of paired relational expressions (as string tuples), one tuple per shared variable.

    Examples
    --------
    >>> pair_relational_expressions("a >= 3 AND b < 10", "a > 2 OR b <= 8")
    [('a >= 3', 'a > 2'), ('b < 10', 'b <= 8')]

    >>> pair_relational_expressions("x == 1", "y == 2")
    []

    Notes
    -----
    - Only pairs expressions that reference the *same* variable name.
    - The order of pairs follows the order of variables in the first expression.
    """
    
    relational_expression_list_1 = _extract_relational_expressions(relational_expression_1)
    relational_expression_list_2 = _extract_relational_expressions(relational_expression_2)
    
    pairs = []
    
    # Extract variable names from leaves
    def extract_variable(leaf):
        return leaf.split()[0]
    
    variables1 = {extract_variable(leaf): leaf for leaf in relational_expression_list_1}
    variables2 = {extract_variable(leaf): leaf for leaf in relational_expression_list_2}
    
    # Create pairs
    for var in variables1:
        if var in variables2:
            pairs.append((variables1[var], variables2[var]))
    
    return pairs

# %%
@trace
def calculate_parameters_similarity(
    conditional_expression_1: str,
    conditional_expression_2: str,
    monitored_parameters_dict: dict,
) -> list[dict]:
    """
    Calculate similarity scores between pairs of relational expressions extracted
    from two conditional expressions.

    This function transforms both input conditional expressions into their 
    Disjunctive Normal Form (DNF), extracts atomic relational expressions, 
    pairs those referring to the same variable, and computes the Jaccard similarity 
    for each pair, based on the provided monitored parameter ranges.

    Parameters
    ----------
    conditional_expression_1 : str
        First conditional expression, which may be a single relational condition
        (e.g., "temperature >= 30") or a compound expression using logical
        operators (e.g., "temperature >= 30 AND battery < 10").
    conditional_expression_2 : str
        Second conditional expression, in the same format as `conditional_expression_1`.
        Example: "temperature < 40 OR humidity == 50".
    monitored_parameters_dict : dict
        Dictionary containing metadata for monitored parameters and their valid ranges.
        For example:
            {
                "temperature": {"min_value": 0, "max_value": 100, "type": "float"},
                "battery": {"min_value": 0, "max_value": 100, "type": "int"}
            }

    Returns
    -------
    list of dict
        A list of dictionaries, each mapping a pair of relational expressions
        (tuple of str) to their Jaccard similarity score (float). Only pairs 
        involving the same variable are included.
        Example:
            [
                {("temperature >= 30", "temperature < 40"): 0.57143},
                {("battery < 10", "battery >= 5"): 0.5}
            ]

    Notes
    -----
    - Similarity is only computed for pairs referring to the same variable.
    - Supported operators: <=, >=, <, >, ==, !=.
    - Each pair is compared using the Jaccard similarity measure over the
      corresponding value ranges.
    - The order of the returned list follows the order of the first expression's variables.

    Examples
    --------
    >>> monitored_params = {
    ...     "a": {"min_value": 0, "max_value": 10, "type": "int"}
    ... }
    >>> calculate_parameters_similarity("a >= 3", "a <= 7", monitored_params)
    [{("a >= 3", "a <= 7"): 0.57143}]
    """

    conditional_expression_1 = conditional_expression_to_dnf(conditional_expression_1, output_operators="text")
    conditional_expression_2 = conditional_expression_to_dnf(conditional_expression_2, output_operators="text")


    pair_relational_expressions_list = pair_relational_expressions(
        conditional_expression_1,
        conditional_expression_2
    )

    matched_relational_expression_and_similarity_dict = []

    for relational_expression_pair in pair_relational_expressions_list:
        relational_expression_1 = relational_expression_pair[0]
        relational_expression_2 = relational_expression_pair[1]

        jaccard_similarity = _calculate_jaccard_similarity(
        relational_expression_1,
        relational_expression_2,
        monitored_parameters_dict)

        matched_relational_expression_and_similarity_dict.append({relational_expression_pair: jaccard_similarity})

    return matched_relational_expression_and_similarity_dict

# %%
@trace
def _extract_parameters(conditional_expression: str) -> List[str]:
    """
    Extract parameter names from a conditional expression string.

    This function parses a conditional expression and returns all unique variable
    names found in the atomic (relational) expressions. Each atomic expression must
    follow the format: <variable> <operator> <value>.

    Supported operators are: ==, !=, <, <=, >, >=. The value is assumed to be numeric.

    Parameters
    ----------
    conditional_expression : str
        A string representing a (possibly compound) conditional expression.
        Example: "a > 10 AND b <= 20 OR c != 5"

    Returns
    -------
    list of str
        List of variable names extracted from the expression, in the order of appearance.

    Examples
    --------
    >>> _extract_parameters("a > 10 AND b <= 20 OR c != 5")
    ['a', 'b', 'c']
    >>> _extract_parameters("x == 1 OR y >= 100")
    ['x', 'y']
    >>> _extract_parameters("battery < 10")
    ['battery']
    """

    relational_expressions = _extract_relational_expressions(conditional_expression)

    variables = []
    for expr in relational_expressions:
        match = re.match(r"([a-zA-Z_]\w*)\s*(==|!=|[<>]=?)\s*([0-9]+)", expr)
        if match:
            variables.append(match.group(1))
    return variables

# %%
def _tversky_similarity(parameter_list_1, parameter_list_2, alpha=1.0, beta=1.0) -> float:
    """
    Compute the Tversky similarity index between two lists of parameters.

    The Tversky index is a generalization of several set similarity measures:
    - If alpha = beta = 1.0, it reduces to the Jaccard index.
    - If alpha = beta = 0.5, it reduces to the Dice coefficient.
    - If alpha != beta, it provides an asymmetric similarity measure.

    Parameters
    ----------
    parameter_list_1 : list of hashable
        First list of parameters (e.g., variable names as strings).
    parameter_list_2 : list of hashable
        Second list of parameters.
    alpha : float, optional
        Weight for elements unique to `parameter_list_1`. Default is 1.0.
    beta : float, optional
        Weight for elements unique to `parameter_list_2`. Default is 1.0.

    Returns
    -------
    float
        Tversky similarity score in the range [0.0, 1.0].
        - 1.0: identical sets
        - 0.0: no overlap

    Notes
    -----
    The formula used is:

        T(A, B) = |A ∩ B| / (|A ∩ B| + alpha * |A \\ B| + beta * |B \\ A|)

    where:
      - |A ∩ B|: number of shared elements between A and B
      - |A \\ B|: elements in A but not in B
      - |B \\ A|: elements in B but not in A

    This metric is useful when asymmetric similarity/dissimilarity penalties are desired.

    Examples
    --------
    >>> _tversky_similarity(['a', 'b', 'c'], ['b', 'c', 'd'])
    0.5
    >>> _tversky_similarity(['a', 'b', 'c'], ['b', 'c', 'd'], alpha=0.7, beta=0.3)
    0.5555555555555556
    >>> _tversky_similarity(['x', 'y'], ['x', 'y'])
    1.0
    >>> _tversky_similarity(['x'], ['y'])
    0.0
    """
    
    set1 = set(parameter_list_1)
    set2 = set(parameter_list_2)

    intersection = len(set1 & set2)
    only_in_set1 = len(set1 - set2)
    only_in_set2 = len(set2 - set1)

    return intersection / (intersection + alpha * only_in_set1 + beta * only_in_set2)

# %%
@trace
def _penalty(parameter_list_1, parameter_list_2, alpha=1.0, beta=1.0) -> float:
    """
    Compute the penalty score as the complement of the Tversky similarity index.

    The penalty quantifies the dissimilarity between two sets of parameters (e.g., variable names).
    It is defined as:

        penalty(A, B) = 1 - Tversky(A, B)

    where `Tversky(A, B)` is the Tversky similarity index.

    Parameters
    ----------
    parameter_list_1 : list of hashable
        First list of parameters (e.g., variable names as strings).
    parameter_list_2 : list of hashable
        Second list of parameters.
    alpha : float, optional
        Weight for elements unique to `parameter_list_1`. Default is 1.0.
    beta : float, optional
        Weight for elements unique to `parameter_list_2`. Default is 1.0.

    Returns
    -------
    float
        Penalty score in the range [0.0, 1.0].
        - 0.0 indicates identical sets (no penalty).
        - Values closer to 1.0 indicate greater dissimilarity.

    Notes
    -----
    This function returns a dissimilarity measure derived from the Tversky index.
    It can be used as a distance-like metric for clustering, anomaly detection,
    or comparing sets of parameters in other analyses.

    Examples
    --------
    >>> _penalty(["a", "b", "c"], ["b", "c", "d"])
    0.5
    >>> _penalty(["a", "b"], ["a", "b"])
    0.0
    >>> _penalty(["x"], ["y"])
    1.0
    >>> _penalty(["a", "b", "c"], ["b", "c", "d"], alpha=0.7, beta=0.3)
    0.4444444444444444
    """
    return 1 - _tversky_similarity(parameter_list_1, parameter_list_2, alpha, beta)

# %%
def _extract_parameter_and_similarity(
    parameter_similarities: List[Dict[Tuple[str, str], float]]
) -> Dict[str, float]:
    """
        Extract variable names and their similarity scores from a list of similarity dictionaries.

        Each dictionary in the input list contains a tuple of relational expressions (leaves) as the key,
        and their similarity value as the value. The variable name is assumed to be the first token in
        the first element of the tuple.

        Parameters
        ----------
        parameter_similarities : list of dict of tuple of (str, str) to float
            List where each item is a dictionary mapping a tuple of two relational expressions (leaves)
            to their similarity score.

        Returns
        -------
        dict of str to float
            Dictionary mapping each variable name (from the first leaf in each tuple) to its similarity score.
            If multiple pairs correspond to the same variable, the last occurrence overwrites previous ones.

        Examples
        --------
        >>> parameter_similarities = [
        ...     {("a >= 3", "a <= 5"): 0.8},
        ...     {("b < 10", "b < 10"): 1.0}
        ... ]
        >>> _extract_parameter_and_similarity(parameter_similarities)
        {'a': 0.8, 'b': 1.0}
        """
    final_parameter_similarity_dict: Dict[str, float] = {}
    for parameter_similarity in parameter_similarities:
        for (leaf1, leaf2), similarity in parameter_similarity.items():
            # Variable is assumed to be the first token in the leaf
            variable = leaf1.split()[0]
            final_parameter_similarity_dict[variable] = similarity
    return final_parameter_similarity_dict

# %%
@trace
def _parameter_similarity_weighted_avg(
    parameter_similarities: List[Dict[Tuple[str, str], float]],
    parameter_weights: Dict[str, float],
    ) -> float:

    """
    Calculate the weighted average similarity across parameters.

    Aggregates the similarity scores from multiple parameter pairs and computes
    a weighted mean, using a dictionary of custom weights per parameter. If a
    parameter does not have a specified weight, it defaults to 1.0.

    Parameters
    ----------
    parameter_similarities : list of dict of tuple of (str, str) to float
        List where each item is a dictionary mapping a tuple of two relational
        expressions (leaves) to their similarity score.
    parameter_weights : dict of str to float
        Dictionary mapping parameter names (extracted from the first token of
        each leaf) to their custom weight. Parameters not present in this
        dictionary use a default weight of 1.0.

    Returns
    -------
    float
        The weighted average similarity across all parameters.
        Returns 0.0 if no weights are available (to avoid division by zero).

    Notes
    -----
    - If the sum of all weights is zero, the function returns 0.0.
    - Later entries for the same parameter in `parameter_similarities`
      overwrite earlier ones.

    Examples
    --------
    >>> parameter_similarities = [
    ...     {("temperature >= 30", "temperature < 40"): 0.57},
    ...     {("battery > 10", "battery != 5"): 0.8}
    ... ]
    >>> parameter_weights = {"temperature": 2.0, "battery": 1.0}
    >>> _parameter_similarity_weighted_avg(parameter_similarities, parameter_weights)
    0.6467
    """

    # Extract a flat mapping of parameter -> similarity
    parameter_and_similarity_dict = _extract_parameter_and_similarity(parameter_similarities)

    weighted_sum = 0.0
    total_weight = 0.0

    for var, similarity in parameter_and_similarity_dict.items():
        weight = parameter_weights.get(var, 1.0)
        weighted_sum += similarity * weight
        total_weight += weight

    if total_weight == 0.0:
        return 0.0  # Avoid division by zero

    weighted_average = weighted_sum / total_weight
    return weighted_average

# %%
@trace
def calculate_conditional_similarity(conditional_expression_1: str,
                                     conditional_expression_2: str,
                                     monitored_parameters_dict: dict,
                                     parameter_weights: dict,
                                     alpha: float = 1.0,
                                     beta: float = 1.0,
                                     ) -> float:
    """
    Calculate the similarity between two conditional expressions using parameter-level
    Jaccard similarity (weighted), penalized by the Tversky dissimilarity of their parameters.

    The similarity is computed in two steps:
      1. **Weighted Jaccard Similarity:** Each pair of relational expressions (sharing the
         same variable) is scored using a weighted Jaccard index, where weights can be
         specified for each parameter.
      2. **Tversky Penalty:** A penalty is subtracted based on the dissimilarity of the
         sets of monitored parameters (using the Tversky index with custom alpha and beta).

    Parameters
    ----------
    conditional_expression_1 : str
        First conditional expression, in a logical format (e.g., "a >= 3 AND b < 10").
    conditional_expression_2 : str
        Second conditional expression to compare.
    monitored_parameters_dict : dict
        Dictionary with metadata for each monitored parameter, in the format:
            {
                "param_name": {"min_value": float, "max_value": float, "type": str},
                ...
            }
    parameter_weights : dict
        Mapping from parameter name (str) to custom weight (float).
        If a parameter is missing, its weight defaults to 1.0.
    alpha : float, optional
        Weight for the elements unique to the first set of parameters in the Tversky index.
        Default is 1.0 (standard Jaccard).
    beta : float, optional
        Weight for the elements unique to the second set of parameters in the Tversky index.
        Default is 1.0.

    Returns
    -------
    float
        Final similarity score in the range [-1.0, 1.0], where higher is more similar.
        Can be negative if penalty outweighs parameter similarity.

    Notes
    -----
    - Each pair of matching parameters (by name) is compared for value-region overlap.
    - Penalty encourages higher similarity only when the set of parameters is also similar.
    - If the intersection of parameters is empty, similarity will be low or negative.

    Examples
    --------
    >>> monitored_params = {
    ...     "a": {"min_value": 0, "max_value": 10, "type": "int"},
    ...     "b": {"min_value": 0, "max_value": 20, "type": "int"},
    ... }
    >>> parameter_weights = {"a": 1.0, "b": 2.0}
    >>> calculate_conditional_similarity(
    ...     "a >= 3 AND b < 10",
    ...     "a >= 5 AND b < 15",
    ...     monitored_params,
    ...     parameter_weights,
    ...     alpha=0.8,
    ...     beta=0.2
    ... )
    0.41053
    """

    parameter_and_similarity_dict = calculate_parameters_similarity(
        conditional_expression_1,
        conditional_expression_2,
        monitored_parameters_dict)
    
    parameter_similarity_avg = _parameter_similarity_weighted_avg(
    parameter_and_similarity_dict,
    parameter_weights=parameter_weights)

    monitored_parameters_1 = _extract_parameters(conditional_expression_1)
    monitored_parameters_2 = _extract_parameters(conditional_expression_2)
    penalty = _penalty(monitored_parameters_1, monitored_parameters_2, alpha=alpha, beta=beta)


    final_similarity = max(parameter_similarity_avg - penalty, 0)

    return final_similarity

# %%
@trace
def calculate_scenario_similarity(scenario_1 :Scenario, sceanrio_2: Scenario, **kwargs) -> float:
    """
    Compute the similarity between two scenarios (ScenarioBDD) by aggregating the similarities
    of their 'given', 'when', and 'then' conditional expressions.

    The similarity of each block is computed via `calculate_conditional_similarity`, which
    considers parameter overlap and semantic distance. The overall scenario similarity is then
    a weighted average of these three block similarities, with custom weights.

    Parameters
    ----------
    scenario_1 : ScenarioBDD
        The first scenario to compare.
    scenario_2 : ScenarioBDD
        The second scenario to compare.
    **kwargs : dict
        Keyword arguments containing weights and additional similarity parameters:
            - conditional_weights : dict
                Weights for each conditional block. Example:
                {"given": 1.0, "when": 1.0, "then": 1.0}
            - tversky_weights : dict
                Alpha/beta weights for Tversky index in conditional similarity. Example:
                {"alpha": 1.0, "beta": 1.0}
            - parameter_weights : dict
                Custom weights for each parameter (str: float). Example:
                {"temperature": 2.0, "humidity": 1.0}
            - monitored_parameters : dict
                Dictionary of parameter metadata as required by conditional similarity.

    Returns
    -------
    float
        The weighted average similarity between the two scenarios, in [0, 1].

    Notes
    -----
    - Each scenario is expected to have `.given`, `.when`, `.then` attributes as ConditionalExpression.
    - Each ConditionalExpression should provide a `.to_string()` method.
    - All blocks are compared independently and combined with provided weights.
    - Typical usage: ranking or matching scenarios by behavioral or semantic similarity.

    Examples
    --------
    >>> kargs = {
    ...     "conditional_weights": {"given": 1.0, "when": 1.0, "then": 1.0},
    ...     "tversky_weights": {"alpha": 1.0, "beta": 1.0},
    ...     "parameter_weights": {"temperature": 1.0, "humidity": 1.0},
    ...     "monitored_parameters": {
    ...         "temperature": {"min_value": 0, "max_value": 100, "type": "float"},
    ...         "humidity": {"min_value": 0, "max_value": 100, "type": "float"},
    ...     }
    ... }
    >>> s1 = ScenarioBDD(...); s2 = ScenarioBDD(...)
    >>> similarity = calculate_scenario_similarity(s1, s2, **kargs)
    >>> print(f"Scenario similarity: {similarity:.3f}")
    0.47

    """

    def weighted_average_conditional_similarity(
        given_similarity: float,
        when_similarity: float,
        then_similarity: float,
        given_weight: float = 1.0,
        when_weight: float = 1.0,
        then_weight: float = 1.0,
    ) -> float:
        

        total_weight = given_weight + when_weight + then_weight
        if total_weight == 0:
            return 0.0

        weighted_avg = (
            (given_similarity * given_weight) +
            (when_similarity * when_weight) +
            (then_similarity * then_weight)
        ) / total_weight

        return weighted_avg


    given_weight = kwargs["conditional_weights"]["given"]
    when_weight = kwargs["conditional_weights"]["when"]
    then_weight = kwargs["conditional_weights"]["then"]
    alpha = kwargs["tversky_weights"]["alpha"]
    beta = kwargs["tversky_weights"]["beta"]
    parameter_weights = kwargs["parameter_weights"]
    monitored_parameters_dict = kwargs["monitored_parameters"]

    given_conditional_expression_1 = scenario_1.given
    given_conditional_expression_2 = sceanrio_2.given

    when_conditional_expression_1 = scenario_1.when
    when_conditional_expression_2 = sceanrio_2.when

    then_conditional_expression_1 = scenario_1.then
    then_conditional_expression_2 = sceanrio_2.then

    given_conditional_similarity = calculate_conditional_similarity(
                                    given_conditional_expression_1.to_string(),
                                    given_conditional_expression_2.to_string(),
                                    monitored_parameters_dict,
                                    parameter_weights,
                                    alpha=alpha,
                                    beta=beta)

    
    when_conditional_similarity = calculate_conditional_similarity(
                                    when_conditional_expression_1.to_string(),
                                    when_conditional_expression_2.to_string(),
                                    monitored_parameters_dict,
                                    parameter_weights,
                                    alpha=alpha,
                                    beta=beta)
    
    then_conditional_similarity = calculate_conditional_similarity(
                                    then_conditional_expression_1.to_string(),
                                    then_conditional_expression_2.to_string(),
                                    monitored_parameters_dict,
                                    parameter_weights,
                                    alpha=alpha,
                                    beta=beta)
    
    scenario_similarity = weighted_average_conditional_similarity(
                            given_conditional_similarity,
                            when_conditional_similarity,
                            then_conditional_similarity,
                            given_weight,
                            when_weight,
                            then_weight)

    return scenario_similarity