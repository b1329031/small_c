# lexer.py
import re

KEYWORDS = {
    'int', 'char', 'void', 'if', 'else', 'while', 'for', 'do',
    'return', 'break', 'continue', 'switch', 'case', 'default', 'struct'
}

TOKEN_SPECS = [
    ('NUMBER',     r'0[xX][0-9a-fA-F]+|\d+'),
    ('STRING',     r'"([^"\\]|\\.)*"'),
    ('CHAR',       r"'([^'\\]|\\.)'"),
    ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('INC',        r'\+\+'),
    ('DEC',        r'--'),
    ('PLUS_EQ',    r'\+='),
    ('MINUS_EQ',   r'-='),
    ('STAR_EQ',    r'\*='),
    ('SLASH_EQ',   r'/='),
    ('PERCENT_EQ', r'%='),
    ('AND_EQ',     r'&='),
    ('OR_EQ',      r'\|='),
    ('XOR_EQ',     r'\^='),
    ('AND_AND',    r'&&'),
    ('OR_OR',      r'\|\|'),
    ('EQ',         r'=='),
    ('NEQ',        r'!='),
    ('LEQ',        r'<='),
    ('GEQ',        r'>='),
    ('LSHIFT',     r'<<'),
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
    ('SKIP',       r'[ \t\r\n]+'),
    ('MISMATCH',   r'.'),
]

_MASTER = re.compile('|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPECS))


class Token:
    __slots__ = ('type', 'value', 'line')

    def __init__(self, type_, value, line=0):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r})'


def strip_comments(code: str) -> str:
    """Remove // and /* */ comments, preserving line counts."""
    result = []
    i = 0
    n = len(code)
    while i < n:
        if code[i] == '/' and i + 1 < n:
            if code[i + 1] == '/':
                # single-line comment
                i += 2
                while i < n and code[i] != '\n':
                    i += 1
                continue
            if code[i + 1] == '*':
                # block comment
                i += 2
                while i < n:
                    if code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                        i += 2
                        break
                    if code[i] == '\n':
                        result.append('\n')
                    i += 1
                continue
        # strings — pass through verbatim so we don't strip inside them
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
    """Substitute #define constants (simple token replacement)."""
    if not defines:
        return code
    # Replace whole-word occurrences
    for name, val in defines.items():
        code = re.sub(r'\b' + re.escape(name) + r'\b', str(val), code)
    return code


def extract_defines(code: str) -> tuple[dict, str]:
    """Pull out #define NAME VALUE lines, return (defines_dict, cleaned_code)."""
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
    code = strip_comments(code)
    if defines:
        code = apply_defines(code, defines)

    tokens = []
    line_num = 1
    for mo in _MASTER.finditer(code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'SKIP':
            line_num += value.count('\n')
            continue
        if kind == 'MISMATCH':
            raise SyntaxError(f"unrecognized character {value!r} at line {line_num}")
        if kind == 'ID' and value in KEYWORDS:
            kind = 'KW'
        tokens.append(Token(kind, value, line_num))
        line_num += value.count('\n')
    return tokens
