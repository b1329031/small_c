# lexer.py
# 詞法分析器：把一串文字切成一個個 token

import re

# Token 類型定義
TOKEN_TYPES = [
    ('NUMBER',    r'0[xX][0-9a-fA-F]+|\d+'),  # 十進位或十六進位
    ('STRING',    r'"([^"\\]|\\.)*"'),           # 字串 "..."
    ('CHAR',      r"'([^'\\]|\\.)'"),            # 字元 'A'
    ('ID',        r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('PLUS',      r'\+'),
    ('MINUS',     r'-'),
    ('STAR',      r'\*'),
    ('SLASH',     r'/'),
    ('PERCENT',   r'%'),
    ('LPAREN',    r'\('),
    ('RPAREN',    r'\)'),
    ('LBRACE',    r'\{'),
    ('RBRACE',    r'\}'),
    ('LBRACKET',  r'\['),
    ('RBRACKET',  r'\]'),
    ('SEMICOLON', r';'),
    ('COMMA',     r','),
    ('SKIP',      r'[ \t\n\r]+'),
]


class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __repr__(self):
        return f'Token({self.type}, {self.value})'

def tokenize(code):
    tokens = []
    i = 0
    while i < len(code):
        match = None
        for token_type, pattern in TOKEN_TYPES:
            regex = re.compile(pattern)
            match = regex.match(code, i)
            if match:
                if token_type != 'SKIP':  # 空白直接跳過
                    tokens.append(Token(token_type, match.group()))
                i = match.end()
                break
        if not match:
            raise SyntaxError(f'無法辨識的字元: {code[i]}')
    return tokens
