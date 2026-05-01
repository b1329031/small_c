# parser.py

class NumberNode:
    def __init__(self, value):
        self.value = int(value)

class BinOpNode:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class VarNode:
    def __init__(self, name):
        self.name = name

class AssignNode:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class CompareNode:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        raise SyntaxError(f'預期 {token_type}，但得到 {token}')

    def parse(self):
        return self.expr()

    def expr(self):
        left = self.add_expr()
        while self.current() and self.current().type in ('EQ','NEQ','LT','GT','LEQ','GEQ'):
            op = self.current().value
            self.pos += 1
            right = self.add_expr()
            left = CompareNode(left, op, right)
        return left

    def add_expr(self):
        left = self.term()
        while self.current() and self.current().type in ('PLUS', 'MINUS'):
            op = self.current().value
            self.pos += 1
            right = self.term()
            left = BinOpNode(left, op, right)
        return left

    def term(self):
        left = self.factor()
        while self.current() and self.current().type in ('STAR', 'SLASH'):
            op = self.current().value
            self.pos += 1
            right = self.factor()
            left = BinOpNode(left, op, right)
        return left

    def factor(self):
        token = self.current()
        if token.type == 'NUMBER':
            self.pos += 1
            return NumberNode(token.value)
        if token.type == 'ID':
            self.pos += 1
            return VarNode(token.value)
        if token.type == 'LPAREN':
            self.pos += 1
            node = self.expr()
            self.eat('RPAREN')
            return node
        raise SyntaxError(f'無法解析: {token}')
