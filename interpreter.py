# interpreter.py
from parser import NumberNode, BinOpNode, VarNode, AssignNode, CompareNode
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
