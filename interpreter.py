# interpreter.py
import math
from ast_nodes import *
# SwitchNode imported via *

# ── control-flow signals ───────────────────────────────────────────
class ReturnSignal(Exception):
    def __init__(self, value=0): self.value = value

class BreakSignal(Exception):    pass
class ContinueSignal(Exception): pass


# ── memory model ───────────────────────────────────────────────────
class Memory:
    def __init__(self):
        self._store = {}
        self._next  = 1000

    def alloc(self, size=1):
        addr = self._next
        for i in range(size):
            self._store[addr + i] = 0
        self._next += size
        return addr

    def read(self, addr):
        if addr not in self._store:
            raise RuntimeError(f"null/invalid pointer dereference (address {addr})")
        return self._store[addr]

    def write(self, addr, value):
        if addr not in self._store:
            raise RuntimeError(f"write to invalid address {addr}")
        self._store[addr] = value

    def reset(self):
        self._store.clear()
        self._next = 1000


# ── symbol / scope ─────────────────────────────────────────────────
class Scope:
    """Holds name→(addr, type, array_size) for one activation frame."""
    def __init__(self, parent=None):
        self._vars  = {}   # name -> {'addr': int, 'type': str, 'size': int}
        self.parent = parent

    def declare(self, name, type_str, addr, array_size=1):
        self._vars[name] = {'addr': addr, 'type': type_str, 'size': array_size}

    def lookup(self, name):
        if name in self._vars:
            return self._vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def all_vars(self):
        return dict(self._vars)


# ── char escape helpers ────────────────────────────────────────────
_ESCAPES = {'n': 10, 't': 9, '0': 0, '\\': 92, "'": 39, '"': 34, 'r': 13}

def _parse_char(raw):
    inner = raw[1:-1]
    if inner.startswith('\\'):
        return _ESCAPES.get(inner[1], ord(inner[1]))
    return ord(inner)

def _unescape_string(s):
    """Convert escape sequences in a string literal (no outer quotes)."""
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


# ── interpreter ────────────────────────────────────────────────────
class Interpreter:
    def __init__(self):
        self.mem          = Memory()
        self.globals      = Scope()
        self.functions    = {}
        self.defines      = {}
        self.trace        = False
        self._source_lines = []            # set by REPL before RUN for trace display
        self._builtins    = {}
        self._call_depth  = 0
        self._MAX_DEPTH   = 500

    # ── public helpers ─────────────────────────────────────────────

    def reset(self):
        self.mem.reset()
        self.globals   = Scope()
        self.functions = {}
        self.defines   = {}
        self._call_depth = 0

    def load_program(self, nodes):
        """Register top-level items (func defs + global var decls)."""
        for node in nodes:
            if isinstance(node, FuncDefNode):
                self.functions[node.name] = node
            elif isinstance(node, VarDeclNode):
                self._exec_var_decl(node, self.globals)

    def exec_interactive(self, nodes):
        """Execute a list of statement/decl nodes in the global scope."""
        for node in nodes:
            self._exec(node, self.globals)

    def run_main(self):
        if 'main' not in self.functions:
            raise RuntimeError("no 'main' function defined")
        ret = self._call_func('main', [])
        return ret if ret is not None else 0

    # ── execution dispatch ─────────────────────────────────────────

    def _exec(self, node, scope):
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
            self.functions[node.name] = node
        elif isinstance(node, ExprStmtNode):
            self._eval(node.expr, scope)
        elif isinstance(node, BlockNode):
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
            raise ReturnSignal(val)
        elif isinstance(node, BreakNode):
            raise BreakSignal()
        elif isinstance(node, ContinueNode):
            raise ContinueSignal()
        elif isinstance(node, SwitchNode):
            self._exec_switch(node, scope)
        else:
            raise RuntimeError(f"unknown node type: {type(node).__name__}")

    def _exec_var_decl(self, node, scope):
        size = node.array_size if node.array_size else 1
        addr = self.mem.alloc(size)
        scope.declare(node.name, node.var_type, addr, size)

        if node.array_size:
            # char buf[N] = "string" initialisation
            if node.init and isinstance(node.init, StringNode):
                s = _unescape_string(node.init.raw[1:-1])
                for i, ch in enumerate(s):
                    if i >= node.array_size: break
                    self.mem.write(addr + i, ord(ch))
                # null terminator
                if len(s) < node.array_size:
                    self.mem.write(addr + len(s), 0)
        else:
            if node.init:
                val = self._eval(node.init, scope)
            else:
                val = 0
            self.mem.write(addr, val)

    def _exec_if(self, node, scope):
        if self._eval(node.cond, scope):
            self._exec(node.then_body, scope)
        elif node.else_body:
            self._exec(node.else_body, scope)

    def _exec_while(self, node, scope):
        while self._eval(node.cond, scope):
            try:
                self._exec(node.body, scope)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_do_while(self, node, scope):
        while True:
            try:
                self._exec(node.body, scope)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if not self._eval(node.cond, scope):
                break

    def _exec_for(self, node, scope):
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
        val = self._eval(node.expr, scope)
        try:
            matched = False
            for case_val, stmts in node.cases:
                if not matched and self._eval(case_val, scope) == val:
                    matched = True
                if matched:
                    for stmt in stmts:
                        self._exec(stmt, scope)
            if not matched and node.default_stmts is not None:
                for stmt in node.default_stmts:
                    self._exec(stmt, scope)
        except BreakSignal:
            pass  # break exits the switch

    # ── expression evaluator ───────────────────────────────────────

    def _eval(self, node, scope):
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, CharNode):
            return _parse_char(node.raw)

        if isinstance(node, StringNode):
            # Allocate a char array, return its base address
            s = _unescape_string(node.raw[1:-1])
            addr = self.mem.alloc(len(s) + 1)
            for i, ch in enumerate(s):
                self.mem.write(addr + i, ord(ch))
            self.mem.write(addr + len(s), 0)
            return addr

        if isinstance(node, VarNode):
            info = scope.lookup(node.name)
            if info is None:
                raise RuntimeError(f"undeclared variable '{node.name}'")
            if info['size'] > 1:
                return info['addr']        # array → base address
            return self.mem.read(info['addr'])

        if isinstance(node, ArrayIndexNode):
            addr = self._array_addr(node, scope)
            return self.mem.read(addr)

        if isinstance(node, DerefNode):
            ptr = self._eval(node.expr, scope)
            return self.mem.read(int(ptr))

        if isinstance(node, AddressOfNode):
            return self._lvalue_addr(node.expr, scope)

        if isinstance(node, AssignNode):
            return self._exec_assign(node, scope)

        if isinstance(node, BinOpNode):
            return self._eval_binop(node, scope)

        if isinstance(node, UnaryNode):
            return self._eval_unary(node, scope)

        if isinstance(node, FuncCallNode):
            return self._call_func(node.name, [self._eval(a, scope) for a in node.args])

        raise RuntimeError(f"cannot evaluate node {type(node).__name__}")

    # ── assignment ─────────────────────────────────────────────────

    def _exec_assign(self, node, scope):
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
            ptr = self._eval(target.expr, scope)
            old = self.mem.read(int(ptr))
            new = self._apply_op(op, old, rval)
            self.mem.write(int(ptr), new)
            return new

        raise RuntimeError(f"invalid assignment target: {type(target).__name__}")

    def _apply_op(self, op, old, rval):
        if op == '=':  return rval
        if op == '+':  return old + rval
        if op == '-':  return old - rval
        if op == '*':  return old * rval
        if op == '/':
            if rval == 0: raise RuntimeError("division by zero")
            return int(old / rval)
        if op == '%':
            if rval == 0: raise RuntimeError("division by zero")
            return int(old - int(old / rval) * rval)
        if op == '&':  return old & rval
        if op == '|':  return old | rval
        if op == '^':  return old ^ rval
        raise RuntimeError(f"unknown assign op '{op}'")

    # ── binary ops ─────────────────────────────────────────────────

    def _eval_binop(self, node, scope):
        op = node.op
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
            return int(L / R)
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

    # ── address helpers ────────────────────────────────────────────

    def _lvalue_addr(self, node, scope):
        if isinstance(node, VarNode):
            info = scope.lookup(node.name)
            if info is None:
                raise RuntimeError(f"undeclared variable '{node.name}'")
            return info['addr']
        if isinstance(node, ArrayIndexNode):
            return self._array_addr(node, scope)
        if isinstance(node, DerefNode):
            return self._eval(node.expr, scope)
        raise RuntimeError(f"cannot take address of {type(node).__name__}")

    def _array_addr(self, node, scope):
        if isinstance(node.name, VarNode):
            info = scope.lookup(node.name.name)
            if info is None:
                raise RuntimeError(f"undeclared array '{node.name.name}'")
            if info['size'] > 1:
                # Actual array: base addr = start of allocated block
                base = info['addr']
                size = info['size']
            else:
                # Pointer variable: read its stored value to get the base addr
                base = self.mem.read(info['addr'])
                size = None  # no bounds check for pointers
        else:
            base = self._eval(node.name, scope)
            size = None

        idx = self._eval(node.index, scope)
        if size is not None and (idx < 0 or idx >= size):
            raise RuntimeError(
                f"array index out of bounds (index {idx}, size {size})")
        return base + idx

    # ── function calls ─────────────────────────────────────────────

    def _call_func(self, name, arg_values):
        if name in self._builtins:
            return self._builtins[name](arg_values)

        if name not in self.functions:
            raise RuntimeError(f"undefined function '{name}'")

        self._call_depth += 1
        if self._call_depth > self._MAX_DEPTH:
            self._call_depth -= 1
            raise RuntimeError("stack overflow (recursion too deep)")

        func = self.functions[name]
        frame = Scope(self.globals)

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
            self._call_depth -= 1

        return ret

    # ── VARS display ───────────────────────────────────────────────

    def show_vars(self):
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

    # ── FUNCS display ──────────────────────────────────────────────

    def show_funcs(self):
        if self.functions:
            for name, f in self.functions.items():
                params = ', '.join(f'{pt} {pn}' for pt, pn in f.params)
                print(f"  {f.ret_type} {name}({params})")
        else:
            print("  (no user-defined functions)")

    # ── trace helper ───────────────────────────────────────────────

    def _node_repr(self, node):
        return type(node).__name__

    # ── string/memory read helpers (used by builtins) ──────────────

    def read_string(self, addr):
        chars = []
        while True:
            c = self.mem.read(addr)
            if c == 0: break
            chars.append(chr(c))
            addr += 1
        return ''.join(chars)

    def write_string(self, addr, s):
        for i, ch in enumerate(s):
            self.mem.write(addr + i, ord(ch))
        self.mem.write(addr + len(s), 0)
