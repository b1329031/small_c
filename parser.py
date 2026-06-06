# parser.py  — recursive-descent parser for Small-C
from ast_nodes import *
# SwitchNode is also imported via *

_COMPOUND_OPS = {
    'PLUS_EQ': '+', 'MINUS_EQ': '-', 'STAR_EQ': '*',
    'SLASH_EQ': '/', 'PERCENT_EQ': '%',
    'AND_EQ': '&', 'OR_EQ': '|', 'XOR_EQ': '^',
}

_TYPE_KW = {'int', 'char', 'void'}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ── token helpers ──────────────────────────────────────────────

    def peek(self, offset=0):
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def current(self):
        return self.peek(0)

    def advance(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def eat(self, *types):
        t = self.current()
        if t and t.type in types:
            return self.advance()
        expected = '/'.join(types)
        got = repr(t) if t else 'EOF'
        raise SyntaxError(f"expected {expected}, got {got}")

    def match(self, *types):
        t = self.current()
        return t is not None and t.type in types

    def match_kw(self, *words):
        t = self.current()
        return t is not None and t.type == 'KW' and t.value in words

    def eat_kw(self, word):
        t = self.current()
        if t and t.type == 'KW' and t.value == word:
            return self.advance()
        raise SyntaxError(f"expected keyword '{word}', got {t!r}")

    # ── type helpers ───────────────────────────────────────────────

    def _is_type_start(self):
        t = self.current()
        return t is not None and t.type == 'KW' and t.value in _TYPE_KW

    def _parse_type(self):
        base = self.eat('KW').value         # int / char / void
        if self.match('STAR'):
            self.advance()
            return base + '*'
        return base

    # ── top-level ──────────────────────────────────────────────────

    def parse_program(self):
        items = []
        while self.current():
            items.append(self._parse_top_level())
        return ProgramNode(items)

    def _parse_top_level(self):
        start_line = self.current().line if self.current() else 0
        type_str = self._parse_type()
        name = self.eat('ID').value

        if self.match('LPAREN'):
            node = self._parse_func_def(type_str, name)
        else:
            node = self._parse_var_decl_tail(type_str, name)
        node._line = start_line
        return node

    def _parse_func_def(self, ret_type, name):
        self.eat('LPAREN')
        params = []
        if not self.match('RPAREN'):
            while True:
                p_type = self._parse_type()
                p_name = self.eat('ID').value
                params.append((p_type, p_name))
                if not self.match('COMMA'):
                    break
                self.advance()
        self.eat('RPAREN')
        body = self._parse_block()
        return FuncDefNode(ret_type, name, params, body.stmts)

    def _parse_var_decl_tail(self, type_str, name):
        array_size = None
        init = None
        if self.match('LBRACKET'):
            self.advance()
            array_size = int(self.eat('NUMBER').value, 0)
            self.eat('RBRACKET')
        elif self.match('ASSIGN'):
            self.advance()
            init = self._parse_expr()
        self.eat('SEMICOLON')
        return VarDeclNode(type_str, name, init, array_size)

    # ── statements ─────────────────────────────────────────────────

    def _parse_block(self):
        self.eat('LBRACE')
        stmts = []
        while not self.match('RBRACE'):
            if self.current() is None:
                raise SyntaxError("missing '}'")
            stmts.append(self._parse_stmt())
        self.eat('RBRACE')
        return BlockNode(stmts)

    def _parse_stmt(self):
        t = self.current()
        if t is None:
            raise SyntaxError('unexpected end of input')
        line = t.line
        node = self._parse_stmt_inner()
        if not hasattr(node, '_line'):
            node._line = line
        return node

    def _parse_stmt_inner(self):
        t = self.current()
        if t is None:
            raise SyntaxError('unexpected end of input')

        if t.type == 'LBRACE':
            return self._parse_block()

        if t.type == 'KW':
            if t.value in _TYPE_KW:
                return self._parse_local_decl()
            if t.value == 'if':       return self._parse_if()
            if t.value == 'while':    return self._parse_while()
            if t.value == 'for':      return self._parse_for()
            if t.value == 'do':       return self._parse_do_while()
            if t.value == 'return':   return self._parse_return()
            if t.value == 'switch':   return self._parse_switch()
            if t.value == 'break':
                self.advance(); self.eat('SEMICOLON')
                return BreakNode()
            if t.value == 'continue':
                self.advance(); self.eat('SEMICOLON')
                return ContinueNode()

        if t.type == 'SEMICOLON':
            self.advance()
            return BlockNode([])

        expr = self._parse_expr()
        self.eat('SEMICOLON')
        return ExprStmtNode(expr)

    def _parse_local_decl(self):
        type_str = self._parse_type()
        name = self.eat('ID').value
        return self._parse_var_decl_tail(type_str, name)

    def _parse_if(self):
        self.eat_kw('if')
        self.eat('LPAREN')
        cond = self._parse_expr()
        self.eat('RPAREN')
        then_body = self._parse_stmt()
        else_body = None
        if self.match_kw('else'):
            self.advance()
            else_body = self._parse_stmt()
        return IfNode(cond, then_body, else_body)

    def _parse_while(self):
        self.eat_kw('while')
        self.eat('LPAREN')
        cond = self._parse_expr()
        self.eat('RPAREN')
        body = self._parse_stmt()
        return WhileNode(cond, body)

    def _parse_do_while(self):
        self.eat_kw('do')
        body = self._parse_stmt()
        self.eat_kw('while')
        self.eat('LPAREN')
        cond = self._parse_expr()
        self.eat('RPAREN')
        self.eat('SEMICOLON')
        return DoWhileNode(body, cond)

    def _parse_for(self):
        self.eat_kw('for')
        self.eat('LPAREN')

        # init
        if self.match('SEMICOLON'):
            init = None; self.advance()
        elif self._is_type_start():
            init = self._parse_local_decl()
        else:
            init = ExprStmtNode(self._parse_expr())
            self.eat('SEMICOLON')

        # cond
        if self.match('SEMICOLON'):
            cond = NumberNode(1); self.advance()
        else:
            cond = self._parse_expr(); self.eat('SEMICOLON')

        # update
        if self.match('RPAREN'):
            update = None
        else:
            update = self._parse_expr()
        self.eat('RPAREN')

        body = self._parse_stmt()
        return ForNode(init, cond, update, body)

    def _parse_return(self):
        self.eat_kw('return')
        if self.match('SEMICOLON'):
            self.advance()
            return ReturnNode(None)
        expr = self._parse_expr()
        self.eat('SEMICOLON')
        return ReturnNode(expr)

    def _parse_switch(self):
        self.eat_kw('switch')
        self.eat('LPAREN')
        expr = self._parse_expr()
        self.eat('RPAREN')
        self.eat('LBRACE')

        cases = []          # [(val_node, [stmts]), ...]
        default_stmts = None

        while not self.match('RBRACE'):
            if self.current() is None:
                raise SyntaxError("missing '}' in switch statement")

            if self.match_kw('case'):
                self.advance()
                val = self._parse_expr()
                self.eat('COLON')
                stmts = []
                while self.current() and not (
                        (self.current().type == 'KW' and self.current().value in ('case', 'default'))
                        or self.current().type == 'RBRACE'):
                    stmts.append(self._parse_stmt())
                cases.append((val, stmts))

            elif self.match_kw('default'):
                self.advance()
                self.eat('COLON')
                default_stmts = []
                while self.current() and not (
                        (self.current().type == 'KW' and self.current().value == 'case')
                        or self.current().type == 'RBRACE'):
                    default_stmts.append(self._parse_stmt())

            else:
                raise SyntaxError(
                    f"expected 'case' or 'default' inside switch, got {self.current()!r}")

        self.eat('RBRACE')
        return SwitchNode(expr, cases, default_stmts)

    # ── expressions (precedence climbing) ─────────────────────────

    def _parse_expr(self):
        return self._parse_assign()

    def _parse_assign(self):
        left = self._parse_logical_or()
        t = self.current()
        if t is None:
            return left
        if t.type == 'ASSIGN':
            self.advance()
            right = self._parse_assign()
            return AssignNode(left, '=', right)
        if t.type in _COMPOUND_OPS:
            op = _COMPOUND_OPS[t.type]
            self.advance()
            right = self._parse_assign()
            return AssignNode(left, op, right)
        return left

    def _binop(self, sub, *types):
        left = sub()
        while self.match(*types):
            op = self.advance().value
            left = BinOpNode(left, op, sub())
        return left

    def _parse_logical_or(self):
        left = self._parse_logical_and()
        while self.match('OR_OR'):
            op = self.advance().value
            left = BinOpNode(left, op, self._parse_logical_and())
        return left

    def _parse_logical_and(self):
        left = self._parse_bitwise_or()
        while self.match('AND_AND'):
            op = self.advance().value
            left = BinOpNode(left, op, self._parse_bitwise_or())
        return left

    def _parse_bitwise_or(self):
        return self._binop(self._parse_bitwise_xor, 'PIPE')

    def _parse_bitwise_xor(self):
        return self._binop(self._parse_bitwise_and, 'CARET')

    def _parse_bitwise_and(self):
        return self._binop(self._parse_equality, 'AMP')

    def _parse_equality(self):
        return self._binop(self._parse_relational, 'EQ', 'NEQ')

    def _parse_relational(self):
        return self._binop(self._parse_shift, 'LT', 'GT', 'LEQ', 'GEQ')

    def _parse_shift(self):
        return self._binop(self._parse_add, 'LSHIFT', 'RSHIFT')

    def _parse_add(self):
        return self._binop(self._parse_mul, 'PLUS', 'MINUS')

    def _parse_mul(self):
        return self._binop(self._parse_unary, 'STAR', 'SLASH', 'PERCENT')

    def _parse_unary(self):
        t = self.current()
        if t and t.type in ('MINUS', 'NOT', 'TILDE'):
            op = self.advance().value
            return UnaryNode(op, self._parse_unary())
        if t and t.type == 'STAR':
            self.advance()
            return DerefNode(self._parse_unary())
        if t and t.type == 'AMP':
            self.advance()
            return AddressOfNode(self._parse_unary())
        if t and t.type == 'INC':
            self.advance()
            operand = self._parse_unary()
            return AssignNode(operand, '=', BinOpNode(operand, '+', NumberNode(1)))
        if t and t.type == 'DEC':
            self.advance()
            operand = self._parse_unary()
            return AssignNode(operand, '=', BinOpNode(operand, '-', NumberNode(1)))
        return self._parse_postfix()

    def _parse_postfix(self):
        node = self._parse_primary()
        while True:
            t = self.current()
            if t and t.type == 'LBRACKET':
                self.advance()
                idx = self._parse_expr()
                self.eat('RBRACKET')
                # node should resolve to a name
                name = node.name if isinstance(node, VarNode) else None
                node = ArrayIndexNode(node, idx)
            elif t and t.type == 'LPAREN' and isinstance(node, VarNode):
                name = node.name
                self.advance()
                args = []
                if not self.match('RPAREN'):
                    args.append(self._parse_expr())
                    while self.match('COMMA'):
                        self.advance()
                        args.append(self._parse_expr())
                self.eat('RPAREN')
                node = FuncCallNode(name, args)
            elif t and t.type == 'INC':
                self.advance()
                node = PostfixIncNode(node, '+')
            elif t and t.type == 'DEC':
                self.advance()
                node = PostfixIncNode(node, '-')
            else:
                break
        return node

    def _parse_primary(self):
        t = self.current()
        if t is None:
            raise SyntaxError('unexpected end of expression')
        if t.type == 'NUMBER':
            self.advance()
            return NumberNode(t.value)
        if t.type == 'CHAR':
            self.advance()
            return CharNode(t.value)
        if t.type == 'STRING':
            self.advance()
            return StringNode(t.value)
        if t.type == 'ID':
            self.advance()
            return VarNode(t.value)
        if t.type == 'KW' and t.value in ('int', 'char', 'void'):
            # sizeof_int() etc handled via FuncCallNode; shouldn't land here
            self.advance()
            return VarNode(t.value)
        if t.type == 'LPAREN':
            self.advance()
            node = self._parse_expr()
            self.eat('RPAREN')
            return node
        raise SyntaxError(f"unexpected token {t!r}")


# ── convenience: parse a single interactive line / snippet ────────

def parse_interactive(tokens):
    """
    Parse one or more statements typed at the REPL prompt.
    Returns a list of statement/decl nodes.
    """
    p = Parser(tokens)
    stmts = []
    while p.current():
        # top-level function definition
        if p._is_type_start():
            saved = p.pos
            try:
                type_str = p._parse_type()
                name = p.eat('ID').value
                if p.match('LPAREN'):
                    stmts.append(p._parse_func_def(type_str, name))
                    continue
                else:
                    stmts.append(p._parse_var_decl_tail(type_str, name))
                    continue
            except SyntaxError:
                p.pos = saved
        stmts.append(p._parse_stmt())
    return stmts
