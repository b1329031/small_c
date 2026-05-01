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

class IfNode:
    def __init__(self, condition, then_body, else_body=None):
        self.condition = condition
        self.then_body = then_body    # list of statements
        self.else_body = else_body    # list of statements 或 None

class WhileNode:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ForNode:
    def __init__(self, init, condition, update, body):
        self.init = init          # int i = 0;
        self.condition = condition # i < 10
        self.update = update      # i = i + 1
        self.body = body          # { ... }



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
    
    def parse_if(self):
        self.eat('LPAREN')
        condition = self.expr()
        self.eat('RPAREN')
        
    # 解析 { ... }
        self.eat('LBRACE')
        then_body = []
        while self.current() and self.current().type != 'RBRACE':
            stmt = self.collect_statement()
            if stmt:
                then_body.append(stmt)
        self.eat('RBRACE')
        
        # 看有沒有 else
        else_body = None
        if self.current() and self.current().value == 'else':
            self.pos += 1
            self.eat('LBRACE')
            else_body = []
            while self.current() and self.current().type != 'RBRACE':
                stmt = self.collect_statement()
                if stmt:
                    else_body.append(stmt)
            self.eat('RBRACE')
        
        return IfNode(condition, then_body, else_body)
    
    def parse_while(self):
        self.eat('LPAREN')
        condition = self.expr()
        self.eat('RPAREN')
        
        self.eat('LBRACE')
        body = []
        while self.current() and self.current().type != 'RBRACE':
            stmt = self.collect_statement()
            if stmt:
                body.append(stmt)
        self.eat('RBRACE')
        
        return WhileNode(condition, body)
    
    def parse_for(self):
        self.eat('LPAREN')
        init = self.collect_statement()   # int i = 0;
        condition = self.expr()           # i < 10
        self.eat('SEMICOLON')
        
        # 手動收集 update（直到遇到 RPAREN）
        update_tokens = []
        while self.current() and self.current().type != 'RPAREN':
            update_tokens.append(self.current())
            self.pos += 1
        update = ' '.join(t.value for t in update_tokens)
        self.eat('RPAREN')
        
        self.eat('LBRACE')
        body = []
        while self.current() and self.current().type != 'RBRACE':
            stmt = self.collect_statement()
            if stmt:
                body.append(stmt)
        self.eat('RBRACE')
        
        return ForNode(init, condition, update, body)

        

    def collect_statement(self):
        tokens = []
        while self.current() and self.current().type not in ('RBRACE',):
            if self.current().type == 'SEMICOLON':
                tokens.append(self.current())
                self.pos += 1
                break
            tokens.append(self.current())
            self.pos += 1
        return ' '.join(t.value for t in tokens)
