# interpreter.py — 直譯器（執行引擎）
# 職責：走訪 AST，執行每個節點所代表的操作
# 資料流：AST → Interpreter → 副作用（輸出、記憶體變更）
#
# 核心設計：
#   Memory  — 以 Python dict 模擬位址空間，地址從 1000 開始遞增
#   Scope   — 鏈結串列形式的符號表，支援多層巢狀作用域
#   _exec   — 執行「語句」（有副作用，不回傳值）
#   _eval   — 求值「運算式」（回傳整數結果）
#   控制流程例外 — return/break/continue 用 Python exception 實作
import math
from ast_nodes import *
# SwitchNode imported via *

# ── 控制流程信號（用例外實作跨層跳躍）───────────────────────────────
# Python 沒有 C 的 goto，用例外可以從深層呼叫棧直接跳出到目標位置

class ReturnSignal(Exception):
    """函式 return：攜帶回傳值，被 _call_func 捕捉"""
    def __init__(self, value=0): self.value = value

class BreakSignal(Exception):
    """break：跳出最內層迴圈或 switch，被迴圈/switch 的執行函式捕捉"""
    pass

class ContinueSignal(Exception):
    """continue：跳到最內層迴圈的下一次迭代，被迴圈執行函式捕捉"""
    pass


# ── 記憶體模型 ─────────────────────────────────────────────────────
class Memory:
    """以 Python dict 模擬虛擬記憶體位址空間。

    alloc(size) 回傳一個起始位址，並在該位址後連續配置 size 個 cell（初始為 0）。
    地址從 1000 開始，避免 0 被誤用為有效地址（0 用作空指標偵測）。
    """
    def __init__(self):
        self._store = {}   # addr -> value
        self._next  = 1000 # 下一個可用地址

    def alloc(self, size=1):
        """配置 size 個連續 cell，回傳起始地址"""
        addr = self._next
        for i in range(size):
            self._store[addr + i] = 0   # 預設初始化為 0
        self._next += size
        return addr

    def read(self, addr):
        """讀取指定地址的值；地址不存在視為空指標取值（執行期錯誤）"""
        if addr not in self._store:
            raise RuntimeError(f"null/invalid pointer dereference (address {addr})")
        return self._store[addr]

    def write(self, addr, value):
        """寫入指定地址；地址不存在視為越界寫入"""
        if addr not in self._store:
            raise RuntimeError(f"write to invalid address {addr}")
        self._store[addr] = value

    def reset(self):
        """清除所有記憶體，重置地址計數（每次 RUN 前呼叫）"""
        self._store.clear()
        self._next = 1000


# ── 符號表（作用域）────────────────────────────────────────────────
class Scope:
    """單一作用域幀，以鏈結串列串接父作用域。

    每個變數條目記錄：addr（記憶體位址）、type（型別字串）、size（配置大小）
    lookup 會沿 parent 鏈向上尋找（實作語彙作用域）。
    """
    def __init__(self, parent=None):
        self._vars  = {}   # name -> {'addr': int, 'type': str, 'size': int}
        self.parent = parent

    def declare(self, name, type_str, addr, array_size=1):
        """在當前幀宣告一個新變數"""
        self._vars[name] = {'addr': addr, 'type': type_str, 'size': array_size}

    def lookup(self, name):
        """由內而外搜尋變數，找不到回傳 None"""
        if name in self._vars:
            return self._vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def all_vars(self):
        return dict(self._vars)


# ── 字元跳脫序列輔助 ───────────────────────────────────────────────
_ESCAPES = {'n': 10, 't': 9, '0': 0, '\\': 92, "'": 39, '"': 34, 'r': 13}

def _parse_char(raw):
    """把字元字面值（如 'A'、'\\n'）轉成整數 ASCII 值"""
    inner = raw[1:-1]
    if inner.startswith('\\'):
        return _ESCAPES.get(inner[1], ord(inner[1]))
    return ord(inner)

def _unescape_string(s):
    """把字串字面值內的跳脫序列展開，如 "hello\\n" → "hello\n"（實際換行）"""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = _ESCAPES.get(s[i+1])
            result.append(chr(c) if c is not None else s[i+1])
            i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


# ── 直譯器主體 ─────────────────────────────────────────────────────
class Interpreter:
    def __init__(self):
        self.mem          = Memory()
        self.globals      = Scope()          # 全域作用域
        self.functions    = {}               # name -> FuncDefNode（使用者定義）
        self.defines      = {}               # #define 常數表
        self.trace        = False            # TRACE ON/OFF 狀態
        self._source_lines = []              # 原始碼行串列，TRACE 顯示用
        self._builtins    = {}               # name -> callable（內建函式）
        self._call_depth  = 0                # 目前呼叫深度，TRACE 縮排用
        self._MAX_DEPTH   = 500              # 遞迴深度上限

    # ── 公開介面 ───────────────────────────────────────────────────

    def reset(self):
        """重置所有執行狀態（每次 RUN 前由 REPL 呼叫）"""
        self.mem.reset()
        self.globals   = Scope()
        self.functions = {}
        self.defines   = {}
        self._call_depth = 0

    def load_program(self, nodes):
        """載入整個程式的頂層項目（函式定義 + 全域變數宣告）"""
        for node in nodes:
            if isinstance(node, FuncDefNode):
                self.functions[node.name] = node    # 記錄函式定義
            elif isinstance(node, VarDeclNode):
                self._exec_var_decl(node, self.globals)  # 配置全域變數記憶體

    def exec_interactive(self, nodes):
        """REPL 互動模式：在全域作用域直接執行語句/宣告"""
        for node in nodes:
            self._exec(node, self.globals)

    def run_main(self):
        """從 main() 函式開始執行程式"""
        if 'main' not in self.functions:
            raise RuntimeError("no 'main' function defined")
        ret = self._call_func('main', [])
        return ret if ret is not None else 0

    # ── 語句執行分派 ───────────────────────────────────────────────

    def _exec(self, node, scope):
        """執行一個語句節點（有副作用，通常不回傳值）。

        TRACE 模式：每個語句執行前先印出行號和原始碼，
        縮排深度由 _call_depth 決定（呼叫越深縮排越多）。
        """
        if self.trace:
            line = getattr(node, '_line', 0)
            if line > 0 and not isinstance(node, BlockNode):
                indent = '  ' * max(0, self._call_depth - 1)
                if self._source_lines and 1 <= line <= len(self._source_lines):
                    src = self._source_lines[line - 1].strip()
                else:
                    src = self._node_repr(node)
                print(f"{indent}[line {line}] {src}")

        if isinstance(node, VarDeclNode):
            self._exec_var_decl(node, scope)
        elif isinstance(node, FuncDefNode):
            self.functions[node.name] = node    # 互動模式中定義函式
        elif isinstance(node, ExprStmtNode):
            self._eval(node.expr, scope)         # 求值運算式語句（取其副作用）
        elif isinstance(node, BlockNode):
            # 區塊建立新的 Scope，讓區域變數的生命週期限於此塊
            inner = Scope(scope)
            for s in node.stmts:
                self._exec(s, inner)
        elif isinstance(node, IfNode):
            self._exec_if(node, scope)
        elif isinstance(node, WhileNode):
            self._exec_while(node, scope)
        elif isinstance(node, DoWhileNode):
            self._exec_do_while(node, scope)
        elif isinstance(node, ForNode):
            self._exec_for(node, scope)
        elif isinstance(node, ReturnNode):
            val = self._eval(node.expr, scope) if node.expr else 0
            raise ReturnSignal(val)     # 用例外跳回 _call_func
        elif isinstance(node, BreakNode):
            raise BreakSignal()         # 用例外跳出迴圈/switch
        elif isinstance(node, ContinueNode):
            raise ContinueSignal()      # 用例外跳到迴圈下一次迭代
        elif isinstance(node, SwitchNode):
            self._exec_switch(node, scope)
        else:
            raise RuntimeError(f"unknown node type: {type(node).__name__}")

    def _exec_var_decl(self, node, scope):
        """執行變數宣告：在 Memory 配置空間，並在 Scope 登記"""
        size = node.array_size if node.array_size else 1
        addr = self.mem.alloc(size)
        scope.declare(node.name, node.var_type, addr, size)

        if node.array_size:
            # 陣列宣告：支援 char buf[50] = "hello" 這種字串初始化
            if node.init and isinstance(node.init, StringNode):
                s = _unescape_string(node.init.raw[1:-1])
                for i, ch in enumerate(s):
                    if i >= node.array_size: break
                    self.mem.write(addr + i, ord(ch))
                if len(s) < node.array_size:
                    self.mem.write(addr + len(s), 0)   # 確保 null terminator
        else:
            # 純量變數：有初始值則求值，否則預設 0（alloc 已初始化）
            if node.init:
                val = self._eval(node.init, scope)
            else:
                val = 0
            self.mem.write(addr, val)

    def _exec_if(self, node, scope):
        """執行 if/else：條件非零則執行 then_body，否則執行 else_body"""
        if self._eval(node.cond, scope):
            self._exec(node.then_body, scope)
        elif node.else_body:
            self._exec(node.else_body, scope)

    def _exec_while(self, node, scope):
        """執行 while 迴圈；BreakSignal 跳出，ContinueSignal 繼續下一輪"""
        while self._eval(node.cond, scope):
            try:
                self._exec(node.body, scope)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_do_while(self, node, scope):
        """執行 do/while 迴圈；先跑一次 body 再檢查條件"""
        while True:
            try:
                self._exec(node.body, scope)
            except BreakSignal:
                break
            except ContinueSignal:
                pass    # continue 只跳過剩餘的 body，仍要檢查條件
            if not self._eval(node.cond, scope):
                break

    def _exec_for(self, node, scope):
        """執行 for 迴圈；init 在新的 Scope 中執行（讓迴圈變數有正確的作用域）"""
        inner = Scope(scope)
        if node.init:
            self._exec(node.init, inner)
        while self._eval(node.cond, inner):
            try:
                self._exec(node.body, inner)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if node.update:
                self._eval(node.update, inner)

    def _exec_switch(self, node, scope):
        """執行 switch/case（加分項目）。

        核心邏輯：用 matched 旗標實作 fall-through。
        一旦某個 case 命中，matched=True，後續的 case 語句都會執行（fall-through），
        直到遇到 break（BreakSignal）或走完所有 case。
        """
        val = self._eval(node.expr, scope)
        try:
            matched = False
            for case_val, stmts in node.cases:
                if not matched and self._eval(case_val, scope) == val:
                    matched = True    # 從這個 case 開始執行
                if matched:
                    for stmt in stmts:
                        self._exec(stmt, scope)
            if not matched and node.default_stmts is not None:
                for stmt in node.default_stmts:
                    self._exec(stmt, scope)
        except BreakSignal:
            pass  # break 正常跳出 switch

    # ── 運算式求值 ─────────────────────────────────────────────────

    def _eval(self, node, scope):
        """求值一個運算式節點，回傳整數結果。

        指標關鍵規則：
        - info['size'] == 1：純量或指標變數，讀取該位址的值
        - info['size'] >  1：真正的陣列，直接回傳起始位址（作為指標傳遞）
        """
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, CharNode):
            return _parse_char(node.raw)

        if isinstance(node, StringNode):
            # 字串字面值：每次求值都重新配置記憶體並填入字元
            # 回傳的是字元陣列的起始位址（char* 指標語意）
            s = _unescape_string(node.raw[1:-1])
            addr = self.mem.alloc(len(s) + 1)
            for i, ch in enumerate(s):
                self.mem.write(addr + i, ord(ch))
            self.mem.write(addr + len(s), 0)   # null terminator
            return addr

        if isinstance(node, VarNode):
            info = scope.lookup(node.name)
            if info is None:
                raise RuntimeError(f"undeclared variable '{node.name}'")
            if info['size'] > 1:
                return info['addr']        # 陣列名稱 → 回傳基底位址（不讀值）
            return self.mem.read(info['addr'])  # 純量/指標 → 讀取位址存的值

        if isinstance(node, ArrayIndexNode):
            addr = self._array_addr(node, scope)
            return self.mem.read(addr)

        if isinstance(node, DerefNode):
            # *ptr：先求得指標值（是個地址），再讀那個地址的值
            ptr = self._eval(node.expr, scope)
            return self.mem.read(int(ptr))

        if isinstance(node, AddressOfNode):
            # &x：回傳 x 的記憶體位址（lvalue 地址）
            return self._lvalue_addr(node.expr, scope)

        if isinstance(node, PostfixIncNode):
            # 後綴 ++/--：先讀舊值，寫入新值，回傳舊值（與前綴 ++ 的差異在此）
            addr = self._lvalue_addr(node.target, scope)
            old = self.mem.read(addr)
            self.mem.write(addr, old + (1 if node.op == '+' else -1))
            return old

        if isinstance(node, AssignNode):
            return self._exec_assign(node, scope)

        if isinstance(node, BinOpNode):
            return self._eval_binop(node, scope)

        if isinstance(node, UnaryNode):
            return self._eval_unary(node, scope)

        if isinstance(node, FuncCallNode):
            return self._call_func(node.name, [self._eval(a, scope) for a in node.args])

        raise RuntimeError(f"cannot evaluate node {type(node).__name__}")

    # ── 指定運算 ───────────────────────────────────────────────────

    def _exec_assign(self, node, scope):
        """執行指定運算（=、+=、-= 等），回傳指定後的新值"""
        rval = self._eval(node.value, scope)
        target = node.target
        op = node.op

        if isinstance(target, VarNode):
            info = scope.lookup(target.name)
            if info is None:
                raise RuntimeError(f"undeclared variable '{target.name}'")
            addr = info['addr']
            old = self.mem.read(addr)
            new = self._apply_op(op, old, rval)
            self.mem.write(addr, new)
            return new

        if isinstance(target, ArrayIndexNode):
            addr = self._array_addr(target, scope)
            old = self.mem.read(addr)
            new = self._apply_op(op, old, rval)
            self.mem.write(addr, new)
            return new

        if isinstance(target, DerefNode):
            # *ptr = val：透過指標寫入
            ptr = self._eval(target.expr, scope)
            old = self.mem.read(int(ptr))
            new = self._apply_op(op, old, rval)
            self.mem.write(int(ptr), new)
            return new

        raise RuntimeError(f"invalid assignment target: {type(target).__name__}")

    def _apply_op(self, op, old, rval):
        """計算複合指定的新值：op='=' 直接取 rval；其餘為 old op rval"""
        if op == '=':  return rval
        if op == '+':  return old + rval
        if op == '-':  return old - rval
        if op == '*':  return old * rval
        if op == '/':
            if rval == 0: raise RuntimeError("division by zero")
            return int(old / rval)   # 模擬 C 的截斷除法
        if op == '%':
            if rval == 0: raise RuntimeError("division by zero")
            return int(old - int(old / rval) * rval)
        if op == '&':  return old & rval
        if op == '|':  return old | rval
        if op == '^':  return old ^ rval
        raise RuntimeError(f"unknown assign op '{op}'")

    # ── 二元運算 ───────────────────────────────────────────────────

    def _eval_binop(self, node, scope):
        """求值二元運算式。
        && 和 || 實作短路求值：若左側已決定結果，不求值右側。
        除法和餘數偵測除以零（加分項目）。
        """
        op = node.op
        # 短路求值：先求左側，再決定是否求右側
        if op == '&&':
            return 1 if (self._eval(node.left, scope) and self._eval(node.right, scope)) else 0
        if op == '||':
            return 1 if (self._eval(node.left, scope) or  self._eval(node.right, scope)) else 0

        L = self._eval(node.left,  scope)
        R = self._eval(node.right, scope)
        if op == '+':   return L + R
        if op == '-':   return L - R
        if op == '*':   return L * R
        if op == '/':
            if R == 0: raise RuntimeError("division by zero")
            return int(L / R)    # 截斷除法（負數朝零）
        if op == '%':
            if R == 0: raise RuntimeError("division by zero")
            return int(L - int(L / R) * R)
        if op == '<':   return 1 if L <  R else 0
        if op == '>':   return 1 if L >  R else 0
        if op == '<=':  return 1 if L <= R else 0
        if op == '>=':  return 1 if L >= R else 0
        if op == '==':  return 1 if L == R else 0
        if op == '!=':  return 1 if L != R else 0
        if op == '<<':  return L << R
        if op == '>>':  return L >> R
        if op == '&':   return L & R
        if op == '|':   return L | R
        if op == '^':   return L ^ R
        raise RuntimeError(f"unknown operator '{op}'")

    def _eval_unary(self, node, scope):
        op = node.op
        v  = self._eval(node.operand, scope)
        if op == '-': return -v
        if op == '!': return 0 if v else 1
        if op == '~': return ~v
        raise RuntimeError(f"unknown unary op '{op}'")

    # ── 位址計算輔助 ───────────────────────────────────────────────

    def _lvalue_addr(self, node, scope):
        """取得 lvalue（可被指定的運算式）的記憶體位址。
        用於取址運算（&x）和後綴 ++/--。"""
        if isinstance(node, VarNode):
            info = scope.lookup(node.name)
            if info is None:
                raise RuntimeError(f"undeclared variable '{node.name}'")
            return info['addr']
        if isinstance(node, ArrayIndexNode):
            return self._array_addr(node, scope)
        if isinstance(node, DerefNode):
            # &(*ptr) → 就是 ptr 本身的值
            return self._eval(node.expr, scope)
        raise RuntimeError(f"cannot take address of {type(node).__name__}")

    def _array_addr(self, node, scope):
        """計算 arr[idx] 的實際記憶體位址，並做陣列越界檢查（加分項目）。

        關鍵區分：
        - size > 1：真正的陣列，base = 配置的起始位址
        - size == 1：指標變數，base = 指標變數存的值（才是陣列的起始位址）
        """
        if isinstance(node.name, VarNode):
            info = scope.lookup(node.name.name)
            if info is None:
                raise RuntimeError(f"undeclared array '{node.name.name}'")
            if info['size'] > 1:
                # 真正的陣列：基底位址 = 配置起點，有大小可做越界檢查
                base = info['addr']
                size = info['size']
            else:
                # 指標參數（如 int *arr）：要讀取指標值才得到基底位址
                base = self.mem.read(info['addr'])
                size = None  # 指標沒有已知大小，無法越界檢查
        else:
            base = self._eval(node.name, scope)
            size = None

        idx = self._eval(node.index, scope)
        if size is not None and (idx < 0 or idx >= size):
            raise RuntimeError(
                f"array index out of bounds (index {idx}, size {size})")
        return base + idx

    # ── 函式呼叫 ───────────────────────────────────────────────────

    def _call_func(self, name, arg_values):
        """執行函式呼叫。

        流程：
        1. 先查內建函式（_builtins）
        2. 再查使用者定義函式（functions）
        3. 建立新的 Scope（frame），父作用域指向 globals（非呼叫者的 scope，實作靜態作用域）
        4. 把引數值複製到 frame 中的參數（call by value）
        5. 用 try/except 捕捉 ReturnSignal 取得回傳值
        """
        if name in self._builtins:
            return self._builtins[name](arg_values)

        if name not in self.functions:
            raise RuntimeError(f"undefined function '{name}'")

        self._call_depth += 1
        if self._call_depth > self._MAX_DEPTH:
            self._call_depth -= 1
            raise RuntimeError("stack overflow (recursion too deep)")

        func = self.functions[name]
        frame = Scope(self.globals)   # 父指向 globals（不是呼叫者的 scope）

        # 把每個引數值複製到新配置的記憶體位址（call by value）
        for (p_type, p_name), val in zip(func.params, arg_values):
            addr = self.mem.alloc(1)
            frame.declare(p_name, p_type, addr)
            self.mem.write(addr, val)

        ret = 0
        try:
            for stmt in func.body:
                self._exec(stmt, frame)
        except ReturnSignal as r:
            ret = r.value
        finally:
            self._call_depth -= 1   # 無論如何都要遞減，避免深度計數錯誤

        return ret

    # ── VARS 顯示 ──────────────────────────────────────────────────

    def show_vars(self):
        """顯示所有全域變數：名稱、型別、當前值；陣列顯示前十個元素"""
        items = self.globals.all_vars()
        if not items:
            print("  (no variables)")
            return
        for name, info in items.items():
            addr  = info['addr']
            t     = info['type']
            size  = info['size']
            if size > 1:
                vals = [self.mem.read(addr + i) for i in range(min(size, 10))]
                vstr = '{' + ', '.join(str(v) for v in vals)
                if size > 10: vstr += ', ...'
                vstr += '}'
                print(f"  {t} {name}[{size}] = {vstr}")
            else:
                val = self.mem.read(addr)
                if t == 'char':
                    if 32 <= val <= 126:
                        print(f"  {t} {name} = {val} ('{chr(val)}')")
                    else:
                        print(f"  {t} {name} = {val}")
                elif t in ('int*', 'char*'):
                    print(f"  {t} {name} = {val}  (-> addr {val})")
                else:
                    print(f"  {t} {name} = {val}")

    # ── FUNCS 顯示 ─────────────────────────────────────────────────

    def show_funcs(self):
        """顯示所有使用者定義函式的簽章"""
        if self.functions:
            for name, f in self.functions.items():
                params = ', '.join(f'{pt} {pn}' for pt, pn in f.params)
                print(f"  {f.ret_type} {name}({params})")
        else:
            print("  (no user-defined functions)")

    # ── TRACE 輔助 ─────────────────────────────────────────────────

    def _node_repr(self, node):
        """當找不到原始碼行時的備用顯示（顯示節點型別名稱）"""
        return type(node).__name__

    # ── 字串/記憶體讀寫（供內建函式使用）────────────────────────

    def read_string(self, addr):
        """從指定記憶體位址讀取 null-terminated 字串"""
        chars = []
        while True:
            c = self.mem.read(addr)
            if c == 0: break
            chars.append(chr(c))
            addr += 1
        return ''.join(chars)

    def write_string(self, addr, s):
        """把字串寫入指定記憶體位址（含 null terminator）"""
        for i, ch in enumerate(s):
            self.mem.write(addr + i, ord(ch))
        self.mem.write(addr + len(s), 0)
