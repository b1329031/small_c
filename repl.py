# repl.py — 互動式 REPL（Read-Eval-Print Loop）
# 職責：提供命令列介面，管理程式緩衝區，分派指令，執行互動式輸入
#
# 架構：
#   REPL.buffer   — 程式碼行的 list[str]，所有指令都操作這個緩衝區
#   REPL.interp   — 持久的 Interpreter 實例（互動模式的全域狀態在此）
#   _cmd_run()    — 每次 RUN 建立全新 Interpreter（確保乾淨的執行環境）
#   _is_complete  — 判斷輸入是否完整（大括號是否都關閉），決定是否顯示續行提示 '  >'
import os, sys, re
from lexer import tokenize, extract_defines, strip_comments
from parser import Parser, parse_interactive
from interpreter import Interpreter, ReturnSignal
from builtin_funcs import register_builtins, BUILTIN_SIGS

WELCOME = """\
========================================
  Small-C Interactive Interpreter v1.0
  System Software Final Project, Spring 2026
  Author: b1329031, b1329033
========================================
Type `HELP` for a list of commands."""

HELP_TEXT = """\
Program management:
  LOAD <file>      Load a Small-C source file into the program buffer
  SAVE <file>      Save the program buffer to a file
  LIST             List all lines in the buffer
  LIST <n>         List line n
  LIST <n1>-<n2>   List lines n1 to n2
  APPEND           Append lines at end of buffer (end with '.' alone)
  INSERT <n>       Insert lines before line n (end with '.' alone)
  EDIT <n>         Edit line n
  DELETE <n>       Delete line n
  DELETE <n1>-<n2> Delete lines n1 to n2
  NEW              Clear buffer and reset all state

Execution & debug:
  RUN              Parse buffer and run main()
  CHECK            Check buffer for syntax errors without running
  TRACE ON         Enable statement-level trace
  TRACE OFF        Disable trace
  VARS             Show all global variables and their values
  FUNCS            Show all defined functions

System:
  HELP             Show this help message
  HELP <cmd>       Show detailed help for a command
  ABOUT            Show interpreter info
  CLEAR            Clear the terminal screen
  QUIT / EXIT      Exit the interpreter"""

# 各指令的詳細說明（HELP <cmd> 用）
COMMAND_HELP = {
    'LOAD':   "LOAD <filename>  — Load a .sc file into the program buffer.",
    'SAVE':   "SAVE <filename>  — Save buffer to a file. Shows line count on success.",
    'LIST':   "LIST / LIST n / LIST n1-n2  — Display buffer contents.",
    'APPEND': "APPEND  — Enter append mode; type lines, end with a lone '.'.",
    'INSERT': "INSERT <n>  — Insert lines before line n; end with a lone '.'.",
    'EDIT':   "EDIT <n>  — Show line n and prompt for replacement.",
    'DELETE': "DELETE <n> / DELETE <n1>-<n2>  — Remove lines from buffer.",
    'NEW':    "NEW  — Clear buffer and reset all interpreter state.",
    'RUN':    "RUN  — Execute the program in the buffer starting from main().",
    'CHECK':  "CHECK  — Check buffer for errors without executing.",
    'TRACE':  "TRACE ON / TRACE OFF  — Toggle statement-level execution trace.",
    'VARS':   "VARS  — List global variables with type and current value.",
    'FUNCS':  "FUNCS  — List user-defined and built-in functions.",
    'ABOUT':  "ABOUT  — Show interpreter name, version, author and semester.",
    'CLEAR':  "CLEAR  — Clear the terminal screen.",
    'QUIT':   "QUIT / EXIT  — Exit the interpreter.",
}


class REPL:
    def __init__(self):
        self.buffer   = []          # 程式碼緩衝區（每個元素是一行字串）
        self.modified = False       # 是否有未儲存的修改（離開時警告用）
        self.interp   = self._make_interp()

    # ── Interpreter 工廠 ───────────────────────────────────────────

    def _make_interp(self, trace=False, defines=None):
        """建立並初始化一個新的 Interpreter，注入所有內建函式"""
        interp = Interpreter()
        register_builtins(interp)
        interp.trace   = trace
        interp.defines = dict(defines) if defines else {}
        return interp

    # ── 主迴圈 ─────────────────────────────────────────────────────

    def run(self):
        """REPL 主迴圈：讀取輸入 → 判斷是指令還是程式碼 → 執行 → 重複"""
        print(WELCOME)
        print()
        pending = []   # 多行輸入的暫存緩衝（等待大括號閉合）

        while True:
            # 若有待完成的多行輸入，顯示續行提示；否則顯示主提示
            prompt = '  > ' if pending else 'sc> '
            try:
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print('\nGoodbye.')
                break

            stripped = line.strip()

            # 指令只在頂層提示（非多行輸入中）才辨識
            if not pending:
                handled = self._dispatch_command(stripped)
                if handled == 'QUIT':
                    break
                if handled:
                    continue

            # 累積多行輸入，等到大括號完整才一次解析執行
            pending.append(line)
            code = '\n'.join(pending)

            if not self._is_complete(code):
                continue          # 大括號未閉合，繼續讀下一行

            pending = []
            self._exec_interactive(code)

    # ── 完整性判斷 ─────────────────────────────────────────────────

    def _is_complete(self, code):
        """判斷輸入的程式碼是否為完整的語法單元。

        策略：
        1. 計算 { } 的深度差，depth > 0 表示有未閉合的大括號
        2. 追蹤 do-while 的 do 是否都有對應的 while
        3. 最後一個非空字元是 ; 或 } 才算完整

        這是啟發式判斷，不做完整語法分析，以快速回應為優先。
        """
        clean = strip_comments(code)
        depth = 0
        do_depth = 0  # 追蹤 do 等待對應的 while

        toks = _rough_tokenize(clean)
        for tok in toks:
            if tok == '{':
                depth += 1
            elif tok == '}':
                depth -= 1
                if depth < 0:
                    depth = 0
            elif tok == 'do':
                do_depth += 1
            elif tok == 'while' and do_depth > 0:
                do_depth -= 1

        if depth > 0:
            return False
        if do_depth > 0:
            return False
        # 大括號平衡時：最後一個字元必須是 ; 或 } 才算完整陳述式
        s = clean.rstrip()
        return bool(s) and (s[-1] in (';', '}'))

    # ── 指令分派 ───────────────────────────────────────────────────

    def _dispatch_command(self, line):
        """判斷輸入是否為 REPL 指令並執行。
        回傳 True（已處理）、'QUIT'（要離開）、或 False（不是指令）。
        """
        up = line.upper()
        parts = line.split()
        if not parts:
            return False

        cmd = parts[0].upper()

        if cmd in ('QUIT', 'EXIT'):
            if self.modified and not self._confirm_discard():
                return True
            print('Goodbye.')
            return 'QUIT'

        if cmd == 'HELP':
            if len(parts) >= 2:
                key = parts[1].upper()
                print(COMMAND_HELP.get(key, f"No help for '{parts[1]}'."))
            else:
                print(HELP_TEXT)
            return True

        if cmd == 'ABOUT':
            print("  Small-C Interactive Interpreter v1.0")
            print("  Course: System Software (Spring 2026)")
            print("  Author: b1329031, b1329033")
            return True

        if cmd == 'CLEAR':
            os.system('cls' if os.name == 'nt' else 'clear')
            return True

        if cmd == 'NEW':
            if self.modified and not self._confirm_discard():
                return True
            self.buffer   = []
            self.modified = False
            # 保留 TRACE 狀態，其餘全部重置
            self.interp   = self._make_interp(trace=self.interp.trace)
            print('All cleared.')
            return True

        if cmd == 'APPEND':
            self._cmd_append()
            return True

        if cmd == 'LIST':
            self._cmd_list(parts[1] if len(parts) >= 2 else None)
            return True

        if cmd == 'EDIT' and len(parts) >= 2:
            self._cmd_edit(parts[1])
            return True

        if cmd == 'DELETE' and len(parts) >= 2:
            self._cmd_delete(parts[1])
            return True

        if cmd == 'INSERT' and len(parts) >= 2:
            self._cmd_insert(parts[1])
            return True

        if cmd == 'SAVE' and len(parts) >= 2:
            self._cmd_save(parts[1])
            return True

        if cmd == 'LOAD' and len(parts) >= 2:
            self._cmd_load(parts[1])
            return True

        if cmd == 'RUN':
            self._cmd_run()
            return True

        if cmd == 'CHECK':
            self._cmd_check()
            return True

        if cmd == 'TRACE':
            if len(parts) >= 2:
                if parts[1].upper() == 'ON':
                    self.interp.trace = True
                    print('Trace mode enabled.')
                elif parts[1].upper() == 'OFF':
                    self.interp.trace = False
                    print('Trace mode disabled.')
                else:
                    print("Usage: TRACE ON / TRACE OFF")
            else:
                print("Usage: TRACE ON / TRACE OFF")
            return True

        if cmd == 'VARS':
            self.interp.show_vars()
            return True

        if cmd == 'FUNCS':
            self._cmd_funcs()
            return True

        return False

    # ── 程式碼緩衝區管理指令 ──────────────────────────────────────

    def _cmd_append(self):
        """在緩衝區末尾追加行，輸入單獨一個 '.' 結束"""
        line_num = len(self.buffer) + 1
        while True:
            try:
                text = input(f'{line_num:4d}> ')
            except EOFError:
                break
            if text.strip() == '.':
                break
            self.buffer.append(text)
            self.modified = True
            line_num += 1

    def _cmd_insert(self, arg):
        """在第 n 行之前插入新行；插入後原有行號向後移"""
        try:
            n = int(arg)
        except ValueError:
            print(f"Error: invalid line number '{arg}'")
            return
        if n < 1 or n > len(self.buffer) + 1:
            print(f"Error: line {n} out of range (buffer has {len(self.buffer)} lines)")
            return
        new_lines = []
        line_num = n
        while True:
            try:
                text = input(f'{line_num:4d}> ')
            except EOFError:
                break
            if text.strip() == '.':
                break
            new_lines.append(text)
            line_num += 1
        if new_lines:
            self.buffer = self.buffer[:n-1] + new_lines + self.buffer[n-1:]
            self.modified = True

    def _cmd_list(self, arg):
        """列出緩衝區內容：無參數列全部，數字列單行，n1-n2 列範圍"""
        if not self.buffer:
            print('(buffer is empty)')
            return
        if arg is None:
            for i, line in enumerate(self.buffer, 1):
                print(f'{i:4d}: {line}')
            return
        if '-' in arg:
            try:
                n1, n2 = arg.split('-', 1)
                n1, n2 = int(n1), int(n2)
            except ValueError:
                print(f"Error: invalid range '{arg}'")
                return
            n1 = max(1, n1)
            n2 = min(len(self.buffer), n2)
            for i in range(n1, n2 + 1):
                print(f'{i:4d}: {self.buffer[i-1]}')
        else:
            try:
                n = int(arg)
            except ValueError:
                print(f"Error: invalid line number '{arg}'")
                return
            if 1 <= n <= len(self.buffer):
                print(f'{n:4d}: {self.buffer[n-1]}')
            else:
                print(f"Error: line {n} out of range")

    def _cmd_edit(self, arg):
        """顯示第 n 行，讓使用者輸入新內容取代；直接按 Enter 保留原行"""
        try:
            n = int(arg)
        except ValueError:
            print(f"Error: invalid line number '{arg}'")
            return
        if not (1 <= n <= len(self.buffer)):
            print(f"Error: line {n} out of range")
            return
        print(f'{n:4d}: {self.buffer[n-1]}')
        try:
            new_text = input(f'{n:4d}> ')
        except EOFError:
            return
        if new_text:               # 空輸入 → 保留原行不變
            self.buffer[n-1] = new_text
            self.modified = True

    def _cmd_delete(self, arg):
        """刪除單行或範圍行；刪除後行號自動重新排列"""
        if '-' in arg:
            try:
                n1, n2 = arg.split('-', 1)
                n1, n2 = int(n1), int(n2)
            except ValueError:
                print(f"Error: invalid range '{arg}'")
                return
            n1 = max(1, n1); n2 = min(len(self.buffer), n2)
            del self.buffer[n1-1:n2]
            self.modified = True
        else:
            try:
                n = int(arg)
            except ValueError:
                print(f"Error: invalid line number '{arg}'")
                return
            if 1 <= n <= len(self.buffer):
                del self.buffer[n-1]
                self.modified = True
            else:
                print(f"Error: line {n} out of range")

    def _cmd_save(self, filename):
        """把緩衝區寫入檔案，清除 modified 旗標"""
        try:
            with open(filename, 'w') as f:
                for line in self.buffer:
                    f.write(line + '\n')
            self.modified = False
            print(f"Saved {len(self.buffer)} lines to '{filename}'.")
        except OSError as e:
            print(f"Error: cannot save '{filename}': {e}")

    def _cmd_load(self, filename):
        """從檔案載入程式碼到緩衝區，同時重置 Interpreter 狀態"""
        if self.modified and not self._confirm_discard():
            return
        try:
            with open(filename) as f:
                lines = f.read().splitlines()
            self.buffer   = lines
            self.modified = False
            self.interp   = self._make_interp(trace=self.interp.trace)
            print(f"Loaded {len(self.buffer)} lines from '{filename}'.")
        except FileNotFoundError:
            print(f"Error: file '{filename}' not found.")
        except OSError as e:
            print(f"Error: cannot load '{filename}': {e}")

    # ── RUN / CHECK ────────────────────────────────────────────────

    def _cmd_run(self):
        """執行緩衝區中的程式。

        關鍵設計：每次 RUN 都建立全新的 Interpreter（run_interp），
        確保全域變數和函式定義從乾淨狀態開始，不受上一次 RUN 殘留的狀態影響。
        TRACE 狀態和 defines 從當前 interp 複製過去。
        _source_lines 設為 buffer，讓 TRACE 能顯示原始碼行。
        """
        if not self.buffer:
            print("Error: program buffer is empty.")
            return

        code = '\n'.join(self.buffer)
        try:
            defines, clean = extract_defines(code)
            run_interp = self._make_interp(trace=self.interp.trace, defines=defines)
            run_interp._source_lines = self.buffer    # 供 TRACE 顯示對應行號的原始碼

            tokens  = tokenize(clean, defines)
            program = Parser(tokens).parse_program()
            run_interp.load_program(program.items)
            ret = run_interp.run_main()
            print(f"Program exited with return value {ret}.")

        except SystemExit as e:
            code_val = e.code if e.code is not None else 0
            print(f"Program exited with return value {code_val}.")
        except SyntaxError as e:
            print(f"Syntax error: {e}")
        except RuntimeError as e:
            print(f"Runtime error: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def _cmd_check(self):
        """只做詞法 + 語法分析，不執行，報告所有錯誤"""
        if not self.buffer:
            print("(buffer is empty)")
            return
        code = '\n'.join(self.buffer)
        try:
            defines, clean = extract_defines(code)
            tokens = tokenize(clean, defines)
            Parser(tokens).parse_program()
            print("No errors found.")
        except SyntaxError as e:
            print(f"Syntax error: {e}")
        except Exception as e:
            print(f"Error: {e}")

    # ── FUNCS 指令 ─────────────────────────────────────────────────

    def _cmd_funcs(self):
        """列出所有使用者定義函式（含行號）和內建函式（標示 [built-in]）。

        行號取自重新解析緩衝區的結果（比 interp.functions 更準確），
        再補上互動模式中即時定義但不在緩衝區的函式。
        """
        from ast_nodes import FuncDefNode as FDN
        user_funcs = {}   # name -> (FuncDefNode, line_in_buffer)

        # 從緩衝區解析取得含行號的函式定義
        if self.buffer:
            try:
                code = '\n'.join(self.buffer)
                defs, clean = extract_defines(code)
                toks = tokenize(clean, defs)
                program = Parser(toks).parse_program()
                for item in program.items:
                    if isinstance(item, FDN):
                        lno = getattr(item, '_line', None)
                        user_funcs[item.name] = (item, lno)
            except Exception:
                pass

        # 補上互動模式定義但不在緩衝區的函式
        for name, f in self.interp.functions.items():
            if name not in user_funcs:
                user_funcs[name] = (f, None)

        if user_funcs:
            col = max(len(f'{f.ret_type} {n}({", ".join(f"{pt} {pn}" for pt,pn in f.params)})')
                      for n, (f, _) in user_funcs.items()) + 2
            for name, (f, lno) in user_funcs.items():
                params = ', '.join(f'{pt} {pn}' for pt, pn in f.params)
                sig = f'{f.ret_type} {name}({params})'
                line_str = f'  line {lno}' if lno else ''
                print(f'  {sig:<{col}}{line_str}')
        else:
            print('  (no user-defined functions)')

        print('  --- built-in functions ---')
        for sig in BUILTIN_SIGS:
            print(f'  {sig:<55}[built-in]')

    # ── 互動執行 ───────────────────────────────────────────────────

    def _exec_interactive(self, code):
        """在持久 Interpreter 上執行互動模式的程式碼片段。

        與 _cmd_run 不同：這裡使用同一個 interp 實例，
        所以互動模式中宣告的變數和函式會跨行保留。
        """
        try:
            defines_new, clean = extract_defines(code)
            self.interp.defines.update(defines_new)   # 累積 #define

            if not clean.strip():
                return

            tokens = tokenize(clean, self.interp.defines)
            if not tokens:
                return

            stmts = parse_interactive(tokens)
            self.interp.exec_interactive(stmts)

        except ReturnSignal:
            pass  # 頂層 return 直接忽略
        except SyntaxError as e:
            print(f"Syntax error: {e}")
        except RuntimeError as e:
            print(f"Runtime error: {e}")
        except SystemExit as e:
            code_val = e.code if e.code is not None else 0
            print(f"Program exited with return value {code_val}.")
        except Exception as e:
            print(f"Error: {e}")

    # ── 輔助方法 ───────────────────────────────────────────────────

    def _confirm_discard(self):
        """提示使用者確認是否放棄未儲存的修改"""
        try:
            ans = input("Buffer has unsaved changes. Discard? (y/n): ")
            return ans.strip().lower() in ('y', 'yes')
        except EOFError:
            return True


# ── 粗略 tokenizer（僅用於完整性判斷）─────────────────────────────

def _rough_tokenize(code):
    """把程式碼拆成粗略的 token 串列，只用於計算大括號深度和 do/while 配對。
    不需要正確處理所有情況，只要能正確識別 {} 和關鍵字即可。"""
    return re.findall(r'[{}]|[a-zA-Z_]\w*|"[^"]*"|\'[^\']*\'|.', code)


def start():
    REPL().run()
