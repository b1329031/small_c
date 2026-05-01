# main.py
import builtin_funcs
from interpreter import run_statement, evaluate, sym
from lexer import tokenize
from parser import Parser, IfNode, WhileNode

def run_if(node):
    condition = evaluate(node.condition)
    if condition:
        for stmt in node.then_body:
            run_statement(stmt, builtin_funcs)
    elif node.else_body:
        for stmt in node.else_body:
            run_statement(stmt, builtin_funcs)

def run_while(node):
    while evaluate(node.condition):
        for stmt in node.body:
            run_statement(stmt, builtin_funcs)

def run(code):
    tokens = tokenize(code)
    p = Parser(tokens)
    
    while p.current():
        token = p.current()
        
        if token.type == 'ID' and token.value == 'if':
            p.pos += 1
            node = p.parse_if()
            run_if(node)
        
        elif token.type == 'ID' and token.value == 'while':
            p.pos += 1
            node = p.parse_while()
            run_while(node)
        
        else:
            stmt = p.collect_statement()
            if stmt:
                run_statement(stmt, builtin_funcs)

# 測試
run('''
int i = 1;
int sum = 0;
while (i <= 10) {
sum = sum + i;
i = i + 1;
}
printf("1+2+...+10 = %d\\n", sum);
''')
