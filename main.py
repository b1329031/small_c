# main.py
import builtin_funcs
from interpreter import run_statement, evaluate, sym
from lexer import tokenize
from parser import Parser, IfNode, WhileNode, ForNode

def run_if(node):
    condition = evaluate(node.condition)
    if condition:
        for stmt in node.then_body: run_statement(stmt, builtin_funcs)
    elif node.else_body:
        for stmt in node.else_body: run_statement(stmt, builtin_funcs)

def run_while(node):
    while evaluate(node.condition):
        for stmt in node.body: run_statement(stmt, builtin_funcs)

def run_for(node):
    run_statement(node.init, builtin_funcs)  # 初始化
    while evaluate(node.condition):           # 條件判斷
        for stmt in node.body:               # 執行本體
            run_statement(stmt, builtin_funcs)
        run_statement(node.update + ';', builtin_funcs)  # 更新

def run(code):
    tokens = tokenize(code)
    p = Parser(tokens)
    while p.current():
        token = p.current()
        if token.type == 'ID' and token.value == 'if':
            p.pos += 1; run_if(p.parse_if())
        elif token.type == 'ID' and token.value == 'while':
            p.pos += 1; run_while(p.parse_while())
        elif token.type == 'ID' and token.value == 'for':
            p.pos += 1; run_for(p.parse_for())
        else:
            stmt = p.collect_statement()
            if stmt: run_statement(stmt, builtin_funcs)

# 測試
run('''
for (int i = 1; i <= 9; i = i + 1) {
printf("%d * %d = %d\n", i, i, i * i);
}
''')
