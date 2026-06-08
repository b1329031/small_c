# parser.py — 遞迴下降解析器（Recursive Descent Parser）
# 職責：把 Token 串列轉成 AST（抽象語法樹）
# 資料流：[Token, ...] → Parser → ProgramNode（包含所有頂層節點）
#
# 運算子優先序（由低到高，共 13 層）：
#  13. 指定（=, +=, -= ...）        右結合
#  12. 邏輯 OR  (||)
#  11. 邏輯 AND (&&)
#  10. 位元 OR  (|)
#   9. 位元 XOR (^)
#   8. 位元 AND (&)
#   7. 相等 (==, !=)
#   6. 關係 (<, >, <=, >=)
#   5. 位移 (<<, >>)
#   4. 加法 (+, -)
#   3. 乘法 (*, /, %)
#   2. 前綴一元（-, !, ~, *, &, ++, --）  右結合
#   1. 後綴（[], (), 後綴++/--）          最高優先
from ast_nodes import *
# SwitchNode is also imported via *

# 複合指定運算子 Token type → 對應的基礎運算子
_COMPOUND_OPS = {
    'PLUS_EQ': '+', 'MINUS_EQ': '-', 'STAR_EQ': '*',
    'SLASH_EQ': '/', 'PERCENT_EQ': '%',
    'AND_EQ': '&', 'OR_EQ': '|', 'XOR_EQ': '^',
}

_TYPE_KW = {'int', 'char', 'void'}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0    # 目前讀到的位置（下一個要看的 token 索引）

    # ── Token 操作輔助方法 ─────────────────────────────────────────

    def peek(self, offset=0):
        """往前偷看（不移動位置）"""
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def current(self):
        return self.peek(0)

    def advance(self):
        """消耗目前 token，回傳它，並移動 pos"""
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def eat(self, *types):
        """期望目前 token 為指定型別之一，否則拋出語法錯誤"""
        t = self.current()
        if t and t.type in types:
            return self.advance()
        expected = '/'.join(types)
        got = repr(t) if t else 'EOF'
        raise SyntaxError(f"expected {expected}, got {got}")

    def match(self, *types):
        """目前 token 是否為指定型別之一（不消耗）"""
        t = self.current()
        return t is not None and t.type in types

    def match_kw(self, *words):
        """目前 token 是否為指定關鍵字之一（不消耗）"""
        t = self.current()
        return t is not None and t.type == 'KW' and t.value in words

    def eat_kw(self, word):
        """期望目前 token 為指定關鍵字，否則拋出語法錯誤"""
        t = self.current()
        if t and t.type == 'KW' and t.value == word:
            return self.advance()
        raise SyntaxError(f"expected keyword '{word}', got {t!r}")

    # ── 型別解析輔助 ───────────────────────────────────────────────

    def _is_type_start(self):
        """目前 token 是否為型別關鍵字（int/char/void）"""
        t = self.current()
        return t is not None and t.type == 'KW' and t.value in _TYPE_KW

    def _parse_type(self):
        """解析型別：int、char、void、int*、char*"""
        base = self.eat('KW').value         # 消耗 int / char / void
        if self.match('STAR'):
            self.advance()
            return base + '*'               # 指標型別
        return base

    # ── 頂層解析 ──────────────────────────────────────────────────

    def parse_program(self):
        """解析完整程式：頂層只允許函式定義與全域變數宣告"""
        items = []
        while self.current():
            items.append(self._parse_top_level())
        return ProgramNode(items)

    def _parse_top_level(self):
        """解析一個頂層項目（函式定義 or 全域變數宣告）
        判斷依據：看到 '(' 就是函式定義，否則是變數宣告"""
        start_line = self.current().line if self.current() else 0
        type_str = self._parse_type()
        name = self.eat('ID').value

        if self.match('LPAREN'):
            node = self._parse_func_def(type_str, name)
        else:
            node = self._parse_var_decl_tail(type_str, name)
        node._line = start_line    # 記錄起始行號，供 TRACE 模式顯示
        return node

    def _parse_func_def(self, ret_type, name):
        """解析函式定義的參數列與函式體"""
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
        """解析變數宣告的後半段（型別與名稱已吃掉）：
        可能是陣列 [N]、有初始值 = expr，或單純的 ;"""
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

    # ── 語句解析 ──────────────────────────────────────────────────

    def _parse_block(self):
        """解析 { ... } 區塊"""
        self.eat('LBRACE')
        stmts = []
        while not self.match('RBRACE'):
            if self.current() is None:
                raise SyntaxError("missing '}'")
            stmts.append(self._parse_stmt())
        self.eat('RBRACE')
        return BlockNode(stmts)

    def _parse_stmt(self):
        """解析一條語句，並記錄行號供 TRACE 顯示"""
        t = self.current()
        if t is None:
            raise SyntaxError('unexpected end of input')
        line = t.line
        node = self._parse_stmt_inner()
        if not hasattr(node, '_line'):
            node._line = line
        return node

    def _parse_stmt_inner(self):
        """語句分派：根據目前 token 決定解析哪種語句"""
        t = self.current()
        if t is None:
            raise SyntaxError('unexpected end of input')

        if t.type == 'LBRACE':
            return self._parse_block()

        if t.type == 'KW':
            if t.value in _TYPE_KW:
                return self._parse_local_decl()    # 區域變數宣告
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
            return BlockNode([])   # 空語句

        # 預設：運算式語句（如 i++; 或 printf(...);）
        expr = self._parse_expr()
        self.eat('SEMICOLON')
        return ExprStmtNode(expr)

    def _parse_local_decl(self):
        """解析函式內部的區域變數宣告"""
        type_str = self._parse_type()
        name = self.eat('ID').value
        return self._parse_var_decl_tail(type_str, name)

    def _parse_if(self):
        """if (cond) stmt [else stmt]"""
        self.eat_kw('if')
        self.eat('LPAREN')
        cond = self._parse_expr()
        self.eat('RPAREN')
        then_body = self._parse_stmt()
        else_body = None
        if self.match_kw('else'):
            self.advance()
            else_body = self._parse_stmt()    # 支援 else if 鏈（遞迴呼叫 _parse_stmt）
        return IfNode(cond, then_body, else_body)

    def _parse_while(self):
        """while (cond) stmt"""
        self.eat_kw('while')
        self.eat('LPAREN')
        cond = self._parse_expr()
        self.eat('RPAREN')
        body = self._parse_stmt()
        return WhileNode(cond, body)

    def _parse_do_while(self):
        """do stmt while (cond);"""
        self.eat_kw('do')
        body = self._parse_stmt()
        self.eat_kw('while')
        self.eat('LPAREN')
        cond = self._parse_expr()
        self.eat('RPAREN')
        self.eat('SEMICOLON')
        return DoWhileNode(body, cond)

    def _parse_for(self):
        """for (init; cond; update) stmt
        三個部分都可省略：for(;;) 代表無窮迴圈"""
        self.eat_kw('for')
        self.eat('LPAREN')

        # init 部分：可以是變數宣告、表達式語句，或省略
        if self.match('SEMICOLON'):
            init = None; self.advance()
        elif self._is_type_start():
            init = self._parse_local_decl()
        else:
            init = ExprStmtNode(self._parse_expr())
            self.eat('SEMICOLON')

        # cond 部分：省略時預設為 1（永遠為真）
        if self.match('SEMICOLON'):
            cond = NumberNode(1); self.advance()
        else:
            cond = self._parse_expr(); self.eat('SEMICOLON')

        # update 部分：可省略
        if self.match('RPAREN'):
            update = None
        else:
            update = self._parse_expr()
        self.eat('RPAREN')

        body = self._parse_stmt()
        return ForNode(init, cond, update, body)

    def _parse_return(self):
        """return [expr];"""
        self.eat_kw('return')
        if self.match('SEMICOLON'):
            self.advance()
            return ReturnNode(None)
        expr = self._parse_expr()
        self.eat('SEMICOLON')
        return ReturnNode(expr)

    def _parse_switch(self):
        """switch (expr) { case val: stmts ... [default: stmts] }
        支援 fall-through（不加 break 會繼續執行下一個 case）"""
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
                # 收集語句，直到遇到下一個 case/default 或 }
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

    # ── 運算式解析（優先序爬升法）────────────────────────────────
    # 每個方法對應一個優先序層級，調用下一層方法取得左運算元

    def _parse_expr(self):
        return self._parse_assign()

    def _parse_assign(self):
        """第 13 層（最低優先）：指定運算子，右結合
        右結合意指 a = b = c 解析為 a = (b = c)，所以遞迴呼叫自身"""
        left = self._parse_logical_or()
        t = self.current()
        if t is None:
            return left
        if t.type == 'ASSIGN':
            self.advance()
            right = self._parse_assign()    # 右結合：遞迴
            return AssignNode(left, '=', right)
        if t.type in _COMPOUND_OPS:
            op = _COMPOUND_OPS[t.type]
            self.advance()
            right = self._parse_assign()    # 右結合：遞迴
            return AssignNode(left, op, right)
        return left

    def _binop(self, sub, *types):
        """左結合二元運算的通用模板：不斷嘗試消耗指定 token，建立 BinOpNode"""
        left = sub()
        while self.match(*types):
            op = self.advance().value
            left = BinOpNode(left, op, sub())
        return left

    def _parse_logical_or(self):
        """第 12 層：|| 短路求值（eval 時由 interpreter 處理短路）"""
        left = self._parse_logical_and()
        while self.match('OR_OR'):
            op = self.advance().value
            left = BinOpNode(left, op, self._parse_logical_and())
        return left

    def _parse_logical_and(self):
        """第 11 層：&& 短路求值"""
        left = self._parse_bitwise_or()
        while self.match('AND_AND'):
            op = self.advance().value
            left = BinOpNode(left, op, self._parse_bitwise_or())
        return left

    def _parse_bitwise_or(self):    return self._binop(self._parse_bitwise_xor, 'PIPE')
    def _parse_bitwise_xor(self):   return self._binop(self._parse_bitwise_and, 'CARET')
    def _parse_bitwise_and(self):   return self._binop(self._parse_equality, 'AMP')
    def _parse_equality(self):      return self._binop(self._parse_relational, 'EQ', 'NEQ')
    def _parse_relational(self):    return self._binop(self._parse_shift, 'LT', 'GT', 'LEQ', 'GEQ')
    def _parse_shift(self):         return self._binop(self._parse_add, 'LSHIFT', 'RSHIFT')
    def _parse_add(self):           return self._binop(self._parse_mul, 'PLUS', 'MINUS')
    def _parse_mul(self):           return self._binop(self._parse_unary, 'STAR', 'SLASH', 'PERCENT')

    def _parse_unary(self):
        """第 2 層：前綴一元運算子，右結合（可連鎖如 !!x、**pp）"""
        t = self.current()
        if t and t.type in ('MINUS', 'NOT', 'TILDE'):
            op = self.advance().value
            return UnaryNode(op, self._parse_unary())
        if t and t.type == 'STAR':
            self.advance()
            return DerefNode(self._parse_unary())       # *ptr
        if t and t.type == 'AMP':
            self.advance()
            return AddressOfNode(self._parse_unary())   # &x
        if t and t.type == 'INC':
            # 前綴 ++：建立 AssignNode（先遞增，再回傳新值）
            # 注意：用 op='=' 而非 op='+'，否則會有雙重加法 bug
            self.advance()
            operand = self._parse_unary()
            return AssignNode(operand, '=', BinOpNode(operand, '+', NumberNode(1)))
        if t and t.type == 'DEC':
            self.advance()
            operand = self._parse_unary()
            return AssignNode(operand, '=', BinOpNode(operand, '-', NumberNode(1)))
        return self._parse_postfix()

    def _parse_postfix(self):
        """第 1 層（最高優先）：後綴運算——陣列索引 []、函式呼叫 ()、後綴 ++/--
        可連鎖，如 arr[i++] 先解析 arr，再套 []，再套後綴 ++"""
        node = self._parse_primary()
        while True:
            t = self.current()
            if t and t.type == 'LBRACKET':
                # 陣列索引：arr[expr]
                self.advance()
                idx = self._parse_expr()
                self.eat('RBRACKET')
                name = node.name if isinstance(node, VarNode) else None
                node = ArrayIndexNode(node, idx)
            elif t and t.type == 'LPAREN' and isinstance(node, VarNode):
                # 函式呼叫：name(arg1, arg2, ...)
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
                # 後綴 ++：PostfixIncNode 在 interpreter 中先回傳舊值再遞增
                self.advance()
                node = PostfixIncNode(node, '+')
            elif t and t.type == 'DEC':
                self.advance()
                node = PostfixIncNode(node, '-')
            else:
                break
        return node

    def _parse_primary(self):
        """最小單元：字面值、識別字、括號運算式"""
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
            self.advance()
            return VarNode(t.value)
        if t.type == 'LPAREN':
            # 括號運算式：(expr)
            self.advance()
            node = self._parse_expr()
            self.eat('RPAREN')
            return node
        raise SyntaxError(f"unexpected token {t!r}")


# ── REPL 互動模式用的解析入口 ────────────────────────────────────

def parse_interactive(tokens):
    """解析 REPL 中輸入的一行或多行程式碼。

    與 parse_program 的差別：這裡同時接受語句（如 printf(...)）
    和頂層函式定義，因為 REPL 兩種輸入都要支援。
    遇到語法錯誤會先嘗試退回重試，以提高容錯性。
    """
    p = Parser(tokens)
    stmts = []
    while p.current():
        # 若以型別關鍵字開頭，可能是函式定義或變數宣告
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
                p.pos = saved   # 解析失敗則退回，改用一般語句解析
        stmts.append(p._parse_stmt())
    return stmts
