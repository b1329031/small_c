from lexer import tokenize
from parser import Parser, NumberNode, BinOpNode
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

class VarNode:
    def __init__(self, name):
        self.name = name

# 讓 parser 也認識變數名稱
# 更新 parser.py 的 factor() 方法
original_factor = Parser.factor

def new_factor(self):
    token = self.current()
    if token.type == 'ID':
        self.pos += 1
        return VarNode(token.value)
    return original_factor(self)

Parser.factor = new_factor

# 執行一行語句
def run_statement(line):
    tokens = tokenize(line)
    if not tokens:
        return

    # int x = 10;
    if tokens[0].value in ('int', 'char'):
        var_type = tokens[0].value
        var_name = tokens[1].value
        if len(tokens) > 3 and tokens[2].type == 'ASSIGN':
            val = evaluate(Parser(tokens[3:-1]).parse())
        else:
            val = 0
        sym.declare(var_name, var_type, val)
        return

    # printf(...)
    if tokens[0].value == 'printf':
        run_printf(tokens, 1)
        return

def run_printf(tokens, pos):
    pos += 1
    fmt = tokens[pos].value[1:-1]
    pos += 1
    args = []
    while tokens[pos].type != 'RPAREN':
        if tokens[pos].type == 'COMMA':
            pos += 1
            continue
        arg_tokens = []
        depth = 0
        while pos < len(tokens):
            t = tokens[pos]
            if t.type == 'COMMA' and depth == 0: break
            if t.type == 'RPAREN' and depth == 0: break
            if t.type == 'LPAREN': depth += 1
            if t.type == 'RPAREN': depth -= 1
            arg_tokens.append(t)
            pos += 1
        if arg_tokens:
            tree = Parser(arg_tokens).parse()
            args.append(evaluate(tree))

    result = ''
    i = 0
    arg_idx = 0
    while i < len(fmt):
        if fmt[i] == '%' and i+1 < len(fmt):
            if fmt[i+1] == 'd':
                result += str(args[arg_idx])
                arg_idx += 1
                i += 2
                continue
        if fmt[i] == '\\' and i+1 < len(fmt):
            if fmt[i+1] == 'n':
                result += '\n'
                i += 2
                continue
        result += fmt[i]
        i += 1
    print(result, end='')

# 測試
run_statement('int x = 10;')
run_statement('int y = 20;')
run_statement('printf("%d\\n", x + y);')
