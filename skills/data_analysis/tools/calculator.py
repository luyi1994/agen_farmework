import ast
import math
import operator
from tools.base import tool

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
}
_SAFE_NAMES = {k: v for k, v in vars(math).items() if not k.startswith("_")}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op)}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        return op(_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        fn_name = node.func.id if isinstance(node.func, ast.Name) else None
        if fn_name in _SAFE_NAMES:
            args = [_safe_eval(a) for a in node.args]
            return _SAFE_NAMES[fn_name](*args)
    if isinstance(node, ast.Name) and node.id in _SAFE_NAMES:
        return _SAFE_NAMES[node.id]
    raise ValueError(f"不安全的表达式节点: {type(node)}")


@tool(name="calculator", description="安全执行数学计算表达式，支持 math 库函数")
def calculator(expression: str) -> str:
    """安全计算数学表达式，如 '2**10'、'sqrt(144)'、'sin(pi/2)'"""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except Exception as e:
        raise ValueError(f"计算失败: {e}，表达式: {expression}")
