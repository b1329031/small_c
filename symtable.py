# symtable.py
# 符號表：記錄所有變數的名稱、型別與值

class SymbolTable:
    def __init__(self):
        self.variables = {}  # { 變數名: {'type': 型別, 'value': 值} }

    def declare(self, name, type, value=0):
        if name in self.variables:
            raise RuntimeError(f'變數 {name} 已經宣告過了')
        self.variables[name] = {'type': type, 'value': value}

    def set(self, name, value):
        if name not in self.variables:
            raise RuntimeError(f'變數 {name} 尚未宣告')
        self.variables[name]['value'] = value

    def get(self, name):
        if name not in self.variables:
            raise RuntimeError(f'變數 {name} 尚未宣告')
        return self.variables[name]['value']
