# ast_nodes.py  — all AST node types

class NumberNode:
    def __init__(self, value):        self.value = int(value, 0) if isinstance(value, str) else value

class StringNode:
    def __init__(self, raw):          self.raw = raw   # includes surrounding quotes

class CharNode:
    def __init__(self, raw):          self.raw = raw

class VarNode:
    def __init__(self, name):         self.name = name

class ArrayIndexNode:
    def __init__(self, name, index):  self.name = name;  self.index = index

class DerefNode:
    def __init__(self, expr):         self.expr = expr

class AddressOfNode:
    def __init__(self, expr):         self.expr = expr   # VarNode or ArrayIndexNode

class BinOpNode:
    def __init__(self, left, op, right): self.left = left; self.op = op; self.right = right

class UnaryNode:
    def __init__(self, op, operand):  self.op = op;  self.operand = operand

class PostfixIncNode:
    """target++ or target--  — evaluates to old value, then mutates target"""
    def __init__(self, target, op): self.target = target; self.op = op  # op: '+' or '-'

class AssignNode:
    """target is VarNode | ArrayIndexNode | DerefNode"""
    def __init__(self, target, op, value): self.target = target; self.op = op; self.value = value

class FuncCallNode:
    def __init__(self, name, args):   self.name = name;  self.args = args

class VarDeclNode:
    """var_type: 'int'|'char'|'int*'|'char*', array_size: int|None"""
    def __init__(self, var_type, name, init=None, array_size=None):
        self.var_type = var_type;  self.name = name
        self.init = init;          self.array_size = array_size

class FuncDefNode:
    def __init__(self, ret_type, name, params, body):
        self.ret_type = ret_type;  self.name = name
        self.params = params       # list of (type_str, param_name)
        self.body = body           # list of statement nodes

class IfNode:
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond;  self.then_body = then_body;  self.else_body = else_body

class WhileNode:
    def __init__(self, cond, body):   self.cond = cond;  self.body = body

class DoWhileNode:
    def __init__(self, body, cond):   self.body = body;  self.cond = cond

class ForNode:
    def __init__(self, init, cond, update, body):
        self.init = init;  self.cond = cond;  self.update = update;  self.body = body

class ReturnNode:
    def __init__(self, expr=None):    self.expr = expr

class BreakNode:    pass
class ContinueNode: pass

class ExprStmtNode:
    def __init__(self, expr):         self.expr = expr

class BlockNode:
    def __init__(self, stmts):        self.stmts = stmts

class SwitchNode:
    """cases: list of (value_node, [stmts])  |  default_stmts: [stmts] | None"""
    def __init__(self, expr, cases, default_stmts=None):
        self.expr = expr
        self.cases = cases
        self.default_stmts = default_stmts

class ProgramNode:
    def __init__(self, items):        self.items = items  # top-level decls/defs
