# builtins.py
from lexer import tokenize
from parser import Parser
from interpreter import evaluate

def run_printf(tokens, pos):
    pos += 1  # 跳過 LPAREN
    fmt = tokens[pos].value[1:-1]  # 去掉引號
    pos += 1

    args = []
    while tokens[pos].type != 'RPAREN':
        if tokens[pos].type == 'COMMA':
            pos += 1
            continue
        arg_tokens = []
        depth = 0
        while pos < len(tokens):
            t = tokens[pos]
            if t.type == 'COMMA' and depth == 0: break
            if t.type == 'RPAREN' and depth == 0: break
            if t.type == 'LPAREN': depth += 1
            if t.type == 'RPAREN': depth -= 1
            arg_tokens.append(t)
            pos += 1
        if arg_tokens:
            tree = Parser(arg_tokens).parse()
            args.append(evaluate(tree))

    # 處理格式字串
    result = ''
    i = 0
    arg_idx = 0
    while i < len(fmt):
        if fmt[i] == '%' and i+1 < len(fmt):
            if fmt[i+1] == 'd':
                result += str(args[arg_idx])
                arg_idx += 1
                i += 2
                continue
        if fmt[i] == '\\' and i+1 < len(fmt):
            if fmt[i+1] == 'n':
                result += '\n'
                i += 2
                continue
        result += fmt[i]
        i += 1
    print(result, end='')
