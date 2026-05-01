# main.py
import builtin_funcs
from interpreter import run_statement, evaluate, sym
from lexer import tokenize
from parser import Parser, IfNode

def run_if(node):
    condition = evaluate(node.condition)
    if condition:
        for stmt in node.then_body:
            run_statement(stmt, builtin_funcs)
    elif node.else_body:
        for stmt in node.else_body:
            run_statement(stmt, builtin_funcs)

def run(code):
    from lexer import tokenize
    from parser import Parser
    tokens = tokenize(code)
    p = Parser(tokens)
    
    while p.current():
        token = p.current()
        
        # if 語句
        if token.type == 'ID' and token.value == 'if':
            p.pos += 1
            node = p.parse_if()
            run_if(node)
        
        # 一般語句
        else:
            stmt = p.collect_statement()
            if stmt:
                run_statement(stmt, builtin_funcs)

# 測試
run('''
int score = 85;
if (score >= 90) {
printf("Grade: A\\n");
} else {
printf("Grade: B\\n");
}
''')
