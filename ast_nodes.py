# ast_nodes.py — 抽象語法樹（AST）節點定義
# 職責：純資料類別，Parser 建立這些物件，Interpreter 讀取並執行
# 每個節點對應一種語言構造，無任何方法邏輯

# ── 運算式節點 ─────────────────────────────────────────────────────

class NumberNode:
    """整數字面值，如 42、-7、0xFF（十六進位）"""
    def __init__(self, value):
        # 若 value 是字串（來自 lexer），用 int(..., 0) 自動處理十六進位/十進位
        self.value = int(value, 0) if isinstance(value, str) else value

class StringNode:
    """字串字面值，如 "hello\n"；raw 含外層雙引號"""
    def __init__(self, raw):          self.raw = raw

class CharNode:
    """字元字面值，如 'A'、'\n'；raw 含外層單引號"""
    def __init__(self, raw):          self.raw = raw

class VarNode:
    """變數讀取，如 x、arr（名稱）"""
    def __init__(self, name):         self.name = name

class ArrayIndexNode:
    """陣列索引，如 arr[i]；name 是陣列的 node（可能是 VarNode 或更複雜的表達式）"""
    def __init__(self, name, index):  self.name = name;  self.index = index

class DerefNode:
    """指標取值（dereference），如 *ptr；expr 是指標運算式"""
    def __init__(self, expr):         self.expr = expr

class AddressOfNode:
    """取址運算，如 &x、&arr[i]；expr 必須是 lvalue（可定址的東西）"""
    def __init__(self, expr):         self.expr = expr

class BinOpNode:
    """二元運算，如 a + b、x == y；op 是運算子字串"""
    def __init__(self, left, op, right): self.left = left; self.op = op; self.right = right

class UnaryNode:
    """前綴一元運算，如 -x、!flag、~mask；op 是運算子字串"""
    def __init__(self, op, operand):  self.op = op;  self.operand = operand

class PostfixIncNode:
    """後綴遞增/遞減，如 i++、j--；
    op='+' 代表 ++，op='-' 代表 --。
    語意：先回傳舊值，再修改 target（與前綴 ++ 不同）"""
    def __init__(self, target, op): self.target = target; self.op = op

class AssignNode:
    """指定運算，如 x = 5、x += 3；
    target 是 lvalue（VarNode | ArrayIndexNode | DerefNode）
    op='=' 是單純指定；op='+'/'-'/... 是複合指定（+=、-= 等）"""
    def __init__(self, target, op, value): self.target = target; self.op = op; self.value = value

class FuncCallNode:
    """函式呼叫，如 printf("hi")、add(a, b)；args 是引數 node 串列"""
    def __init__(self, name, args):   self.name = name;  self.args = args

# ── 宣告節點 ────────────────────────────────────────────────────────

class VarDeclNode:
    """變數宣告，如 int x = 10;、char buf[50];
    var_type: 'int'|'char'|'int*'|'char*'
    array_size: None 表示純量/指標；整數表示一維陣列大小"""
    def __init__(self, var_type, name, init=None, array_size=None):
        self.var_type = var_type;  self.name = name
        self.init = init;          self.array_size = array_size

class FuncDefNode:
    """函式定義，如 int add(int a, int b) { ... }
    params: [(type_str, param_name), ...] 的串列"""
    def __init__(self, ret_type, name, params, body):
        self.ret_type = ret_type;  self.name = name
        self.params = params       # list of (type_str, param_name)
        self.body = body           # list of statement nodes

# ── 控制流程節點 ────────────────────────────────────────────────────

class IfNode:
    """if/else，then_body 和 else_body 都是 stmt node（else 可為 None）"""
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond;  self.then_body = then_body;  self.else_body = else_body

class WhileNode:
    """while 迴圈：先測條件，再執行 body"""
    def __init__(self, cond, body):   self.cond = cond;  self.body = body

class DoWhileNode:
    """do/while 迴圈：先執行 body，再測條件（至少執行一次）"""
    def __init__(self, body, cond):   self.body = body;  self.cond = cond

class ForNode:
    """for 迴圈：init/cond/update 各有獨立 node，任一可為 None"""
    def __init__(self, init, cond, update, body):
        self.init = init;  self.cond = cond;  self.update = update;  self.body = body

class ReturnNode:
    """return 語句；expr=None 代表 void return"""
    def __init__(self, expr=None):    self.expr = expr

class BreakNode:    pass   # break;
class ContinueNode: pass   # continue;

# ── 結構節點 ────────────────────────────────────────────────────────

class ExprStmtNode:
    """運算式語句（表達式後加分號），如 i++;、printf(...)；"""
    def __init__(self, expr):         self.expr = expr

class BlockNode:
    """大括號區塊 { stmt1; stmt2; ... }；stmts 是 stmt node 串列"""
    def __init__(self, stmts):        self.stmts = stmts

class SwitchNode:
    """switch/case（加分項目）
    cases: [(value_node, [stmts]), ...] — 每個 case 的值與對應語句
    default_stmts: [stmts] | None — default 分支（可無）
    支援 fall-through 與 break 跳出"""
    def __init__(self, expr, cases, default_stmts=None):
        self.expr = expr
        self.cases = cases
        self.default_stmts = default_stmts

class ProgramNode:
    """整個程式的頂層節點，items 包含所有函式定義與全域變數宣告"""
    def __init__(self, items):        self.items = items
