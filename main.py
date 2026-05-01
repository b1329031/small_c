# main.py
from lexer import tokenize
from parser import Parser
from interpreter import evaluate, sym
from builtin_funcs import run_printf


def run_statement(line):
    line = line.strip()
    if not line:
        return
    
    tokens = tokenize(line)
    if not tokens:
        return

    # 變數宣告 int x = 10;
    if tokens[0].value in ('int', 'char'):
        var_type = tokens[0].value
        var_name = tokens[1].value
        if len(tokens) > 3 and tokens[2].type == 'ASSIGN':
            val = evaluate(Parser(tokens[3:-1]).parse())
        else:
            val = 0
        sym.declare(var_name, var_type, val)
        return

    # printf
    if tokens[0].value == 'printf':
        run_printf(tokens, 1)
        return

# 測試
run_statement('int x = 10;')
run_statement('int y = 20;')
run_statement('printf("%d\\n", x + y);')
