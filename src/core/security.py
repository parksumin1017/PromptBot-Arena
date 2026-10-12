"""Security Sandbox for Policy Code Execution.

Strictly implements specifications from docs/design.md Section 6:
- Section 6.1: AST NodeVisitor Whitelist Validator
- Section 6.2: Watchdog 100ms Runtime Execution Timeout
"""

import ast
import threading
from typing import Callable, Any, Tuple, Optional, Set
from src.core.models import State, ActionCommand
from src.core.primitives import stop


# ---------------------------------------------------------------------------
# 6.1 AST Whitelist Node Specification (docs/design.md Section 6.1)
# ---------------------------------------------------------------------------

ALLOWED_AST_NODES = (
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.If,
    ast.IfExp,
    ast.Pass,
    ast.Assign,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.Tuple,
    ast.List,
    ast.Compare,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
    ast.Expr,
    ast.keyword,
    # Comparison and math operators
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.And, ast.Or, ast.Not,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.USub, ast.UAdd
)

ALLOWED_CALLABLE_NAMES: Set[str] = {
    # Action Primitives
    "push", "move_to", "stop", "will_collide",
    "get_dist", "get_closest_puck", "get_pucks_in_zone",
    # Safe Python Built-ins
    "min", "max", "abs", "round", "len", "float", "int", "bool"
}

FORBIDDEN_NAME_PREFIXES = ("__",)


class ASTSecurityValidator(ast.NodeVisitor):
    """
    Validates Python AST against strict whitelist before execution.
    Rejects imports, dunder methods, eval/exec/open, and loops by default.
    Permits locally defined helper functions.
    """

    def __init__(self, defined_functions: Optional[Set[str]] = None):
        self.errors: list[str] = []
        self.has_policy_step: bool = False
        self.defined_functions: Set[str] = set(defined_functions) if defined_functions else set()

    def generic_visit(self, node: ast.AST):
        if not isinstance(node, ALLOWED_AST_NODES):
            self.errors.append(f"Forbidden syntax element: {type(node).__name__}")
        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name.startswith("__"):
            self.errors.append(f"Forbidden dunder function name: '{node.name}'")
        if node.name == "policy_step":
            if len(node.args.args) != 1 or node.args.args[0].arg != "state":
                self.errors.append("Function 'policy_step' must accept exactly one argument named 'state'")
            else:
                self.has_policy_step = True
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        self.errors.append("Forbidden import statement.")

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.errors.append("Forbidden from ... import statement.")

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__"):
            self.errors.append(f"Forbidden dunder attribute access: {node.attr}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Verify function call target
        if isinstance(node.func, ast.Name):
            if node.func.id not in ALLOWED_CALLABLE_NAMES and node.func.id not in self.defined_functions:
                self.errors.append(f"Unauthorized function call: '{node.func.id}()'")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr.startswith("__"):
                self.errors.append(f"Forbidden dunder method call: '{node.func.attr}()'")
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.errors.append("Forbidden while loop (infinite loop prevention).")

    def visit_For(self, node: ast.For):
        # Disallow for loops to avoid long-running execution inside 10ms budget
        self.errors.append("Forbidden for loop (use helper primitives).")


def validate_policy_ast(code_str: str) -> Tuple[bool, Optional[str]]:
    """
    Parse and validate policy python code.
    Returns (is_valid, error_message).
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Pre-collect all locally defined function names in this code
    defined_functions: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_functions.add(node.name)

    validator = ASTSecurityValidator(defined_functions=defined_functions)
    validator.visit(tree)

    if not validator.has_policy_step:
        validator.errors.append("Missing required function definition: 'def policy_step(state):'")

    if validator.errors:
        return False, "; ".join(validator.errors)

    return True, None


# ---------------------------------------------------------------------------
# 6.2 Watchdog Execution Timeout (docs/design.md Section 6.2)
# ---------------------------------------------------------------------------

WATCHDOG_TIMEOUT_SECONDS = 0.100  # 100 ms hard limit


def execute_policy_with_watchdog(
    policy_func: Callable[[State], ActionCommand],
    state: State,
    timeout: float = WATCHDOG_TIMEOUT_SECONDS
) -> ActionCommand:
    """
    Execute policy_step with strict watchdog timeout.
    Returns stop() if timeout or runtime exception occurs.
    """
    result_container: list[ActionCommand] = []
    exception_container: list[Exception] = []

    def target_worker():
        try:
            cmd = policy_func(state)
            result_container.append(cmd)
        except Exception as e:
            exception_container.append(e)

    thread = threading.Thread(target=target_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Timeout occurred (Watchdog Triggered)
        return stop()

    if exception_container or not result_container:
        # Runtime error in user code
        return stop()

    action = result_container[0]
    if not isinstance(action, ActionCommand):
        return stop()

    return action
