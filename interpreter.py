# interpreter.py
from parser import NumberNode, BinOpNode, VarNode, AssignNode, CompareNode, IfNode
from symtable import SymbolTable

sym = SymbolTable()

def evaluate(node):
    if isinstance(node, NumberNode):
        return node.value
    if isinstance(node, BinOpNode):
        left = evaluate(node.left)
        right = evaluate(node.right)
        if node.op == '+': return left + right
        if node.op == '-': return left - right
        if node.op == '*': return left * right
        if node.op == '/': return left // right
    if isinstance(node, VarNode):
        return sym.get(node.name)
    if isinstance(node, AssignNode):
        val = evaluate(node.value)
        sym.set(node.name, val)
        return val
    if isinstance(node, CompareNode):
        left = evaluate(node.left)
        right = evaluate(node.right)
        if node.op == '>':  return 1 if left > right else 0
        if node.op == '<':  return 1 if left < right else 0
        if node.op == '==': return 1 if left == right else 0
        if node.op == '!=': return 1 if left != right else 0
        if node.op == '>=': return 1 if left >= right else 0
        if node.op == '<=': return 1 if left <= right else 0

def run_statement(stmt, builtin_funcs):
    from lexer import tokenize
    from parser import Parser

    line = stmt.strip()
    if not line:
        return

    tokens = tokenize(line)
    if not tokens:
        return

    # 變數宣告
    if tokens[0].value in ('int', 'char'):
        var_type = tokens[0].value
        var_name = tokens[1].value
        if len(tokens) > 3 and tokens[2].type == 'ASSIGN':
            val = evaluate(Parser(tokens[3:-1]).parse())
        else:
            val = 0
        sym.declare(var_name, var_type, val)
        return
    
    # 變數指定 x = x + 1;
    if len(tokens) >= 3 and tokens[1].type == 'ASSIGN':
        var_name = tokens[0].value
        val = evaluate(Parser(tokens[2:-1]).parse())
        sym.set(var_name, val)
        return

    # printf
    if tokens[0].value == 'printf':
        builtin_funcs.run_printf(tokens, 1)
        return
