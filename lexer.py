# lexer.py — 詞法分析器
# 職責：把原始碼字串切成 Token 串列，供 Parser 使用
# 資料流：原始碼字串 → strip_comments → apply_defines → regex 掃描 → [Token, ...]
import re

# Small-C 的保留關鍵字集合，tokenize 時會把符合的 ID 改標為 KW
KEYWORDS = {
    'int', 'char', 'void', 'if', 'else', 'while', 'for', 'do',
    'return', 'break', 'continue', 'switch', 'case', 'default', 'struct'
}

# Token 規格表：(type名稱, regex)
# 順序非常重要：越長、越優先的 pattern 必須放越前面
# 例如 '++' 要在 '+' 之前，'==' 要在 '=' 之前，否則會被拆成兩個短 token
TOKEN_SPECS = [
    ('NUMBER',     r'0[xX][0-9a-fA-F]+|\d+'),   # 十六進位(0x...) 或十進位整數
    ('STRING',     r'"([^"\\]|\\.)*"'),            # 雙引號字串，支援跳脫序列
    ('CHAR',       r"'([^'\\]|\\.)'"),             # 單引號字元常數
    ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),    # 識別字（函式名、變數名）
    ('INC',        r'\+\+'),    # ++ 必須在 + 前面
    ('DEC',        r'--'),      # -- 必須在 - 前面
    ('PLUS_EQ',    r'\+='),
    ('MINUS_EQ',   r'-='),
    ('STAR_EQ',    r'\*='),
    ('SLASH_EQ',   r'/='),
    ('PERCENT_EQ', r'%='),
    ('AND_EQ',     r'&='),
    ('OR_EQ',      r'\|='),
    ('XOR_EQ',     r'\^='),
    ('AND_AND',    r'&&'),      # 邏輯 AND，必須在 & 之前
    ('OR_OR',      r'\|\|'),    # 邏輯 OR，必須在 | 之前
    ('EQ',         r'=='),      # 相等比較，必須在 = 之前
    ('NEQ',        r'!='),
    ('LEQ',        r'<='),
    ('GEQ',        r'>='),
    ('LSHIFT',     r'<<'),      # 位移，必須在 < 之前
    ('RSHIFT',     r'>>'),
    ('PLUS',       r'\+'),
    ('MINUS',      r'-'),
    ('STAR',       r'\*'),
    ('SLASH',      r'/'),
    ('PERCENT',    r'%'),
    ('AMP',        r'&'),
    ('PIPE',       r'\|'),
    ('CARET',      r'\^'),
    ('TILDE',      r'~'),
    ('NOT',        r'!'),
    ('LT',         r'<'),
    ('GT',         r'>'),
    ('ASSIGN',     r'='),
    ('LPAREN',     r'\('),
    ('RPAREN',     r'\)'),
    ('LBRACE',     r'\{'),
    ('RBRACE',     r'\}'),
    ('LBRACKET',   r'\['),
    ('RBRACKET',   r'\]'),
    ('SEMICOLON',  r';'),
    ('COMMA',      r','),
    ('DOT',        r'\.'),
    ('COLON',      r':'),
    ('HASH',       r'#'),
    ('SKIP',       r'[ \t\r\n]+'),   # 空白、換行：只用來計算行號，不產生 token
    ('MISMATCH',   r'.'),            # 不認識的字元：報錯
]

# 把所有 pattern 合併成一個大 regex，用具名群組 (?P<TYPE>...) 區分
# re 會依序嘗試每個 alternative，命中第一個就停止，所以順序才重要
_MASTER = re.compile('|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPECS))


class Token:
    """詞法單元：帶有 type、value、行號的資料物件"""
    __slots__ = ('type', 'value', 'line')

    def __init__(self, type_, value, line=0):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r})'


def strip_comments(code: str) -> str:
    """移除 // 單行註解與 /* */ 區塊註解，但保留換行符以維持行號正確。

    同時處理字串字面值內部的 /，確保字串裡的 // 或 /* 不被誤刪。
    """
    result = []
    i = 0
    n = len(code)
    while i < n:
        if code[i] == '/' and i + 1 < n:
            if code[i + 1] == '/':
                # 單行註解：跳過直到行尾（換行本身保留給行號計數）
                i += 2
                while i < n and code[i] != '\n':
                    i += 1
                continue
            if code[i + 1] == '*':
                # 區塊註解：跳過內容，但遇到換行時補回去，保持行號對應
                i += 2
                while i < n:
                    if code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                        i += 2
                        break
                    if code[i] == '\n':
                        result.append('\n')
                    i += 1
                continue
        # 字串字面值：原樣保留（裡面的 / 不能被誤判成註解）
        if code[i] == '"':
            result.append(code[i])
            i += 1
            while i < n:
                result.append(code[i])
                if code[i] == '\\':
                    i += 1
                    if i < n:
                        result.append(code[i])
                elif code[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if code[i] == "'":
            result.append(code[i])
            i += 1
            while i < n:
                result.append(code[i])
                if code[i] == '\\':
                    i += 1
                    if i < n:
                        result.append(code[i])
                elif code[i] == "'":
                    i += 1
                    break
                i += 1
            continue
        result.append(code[i])
        i += 1
    return ''.join(result)


def apply_defines(code: str, defines: dict) -> str:
    """將 #define 常數做整字替換（whole-word replacement）。

    用 \\b 邊界確保 SIZE 不會誤替換到 SIZES、RESIZE 等包含 SIZE 的識別字。
    """
    if not defines:
        return code
    for name, val in defines.items():
        code = re.sub(r'\b' + re.escape(name) + r'\b', str(val), code)
    return code


def extract_defines(code: str) -> tuple[dict, str]:
    """掃描程式碼，抽出所有 #define NAME VALUE 行。

    回傳 (defines字典, 移除#define行後的乾淨程式碼)。
    注意：移除 #define 行時不補空行，所以 parser 拿到的行號
    會比 REPL buffer 的行號少（每個 #define 少 1 行），這是預期行為。
    """
    defines = {}
    lines = []
    for line in code.split('\n'):
        m = re.match(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+)', line)
        if m:
            defines[m.group(1)] = m.group(2).strip()
        else:
            lines.append(line)
    return defines, '\n'.join(lines)


def tokenize(code: str, defines: dict | None = None) -> list[Token]:
    """主入口：把原始碼轉成 Token 串列。

    流程：
    1. strip_comments：移除 // 和 /* */ 註解
    2. apply_defines：#define 常數替換
    3. _MASTER regex 掃描：每個命中產生一個 Token
    """
    code = strip_comments(code)
    if defines:
        code = apply_defines(code, defines)

    tokens = []
    line_num = 1
    for mo in _MASTER.finditer(code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'SKIP':
            line_num += value.count('\n')   # 空白不產生 token，只更新行號
            continue
        if kind == 'MISMATCH':
            raise SyntaxError(f"unrecognized character {value!r} at line {line_num}")
        if kind == 'ID' and value in KEYWORDS:
            kind = 'KW'    # 關鍵字與識別字共用同一 regex，在這裡區分
        tokens.append(Token(kind, value, line_num))
        line_num += value.count('\n')
    return tokens
