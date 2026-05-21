# repl.py
import os, sys, re
from lexer import tokenize, extract_defines, strip_comments
from parser import Parser, parse_interactive
from interpreter import Interpreter, ReturnSignal
from builtin_funcs import register_builtins, BUILTIN_SIGS

WELCOME = """\
========================================
  Small-C Interactive Interpreter v1.0
  System Software Final Project, Spring 2026
  Author: b1329031
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
        self.buffer   = []          # program buffer (list of str)
        self.modified = False       # unsaved changes
        self.interp   = self._make_interp()

    # ── interpreter factory ────────────────────────────────────────

    def _make_interp(self, trace=False, defines=None):
        interp = Interpreter()
        register_builtins(interp)
        interp.trace   = trace
        interp.defines = dict(defines) if defines else {}
        return interp

    # ── entry point ────────────────────────────────────────────────

    def run(self):
        print(WELCOME)
        print()
        pending = []   # lines accumulating for multi-line interactive input

        while True:
            prompt = '  > ' if pending else 'sc> '
            try:
                line = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print('\nGoodbye.')
                break

            stripped = line.strip()

            # ── REPL commands only accepted at the top-level prompt ──
            if not pending:
                handled = self._dispatch_command(stripped)
                if handled == 'QUIT':
                    break
                if handled:
                    continue

            # ── interactive code accumulation ──────────────────────
            pending.append(line)
            code = '\n'.join(pending)

            if not self._is_complete(code):
                continue          # need more input

            pending = []
            self._exec_interactive(code)

    # ── completeness heuristic ─────────────────────────────────────

    def _is_complete(self, code):
        """True when the code looks like a complete unit."""
        clean = strip_comments(code)
        depth = 0
        in_str = in_char = False
        esc = False
        do_depth = 0  # track 'do' blocks awaiting 'while'

        i = 0
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
        # Depth is 0: complete if last non-whitespace is ';' or '}'
        s = clean.rstrip()
        return bool(s) and (s[-1] in (';', '}'))

    # ── command dispatcher ─────────────────────────────────────────

    def _dispatch_command(self, line):
        """Return True/'QUIT' if handled as a command, False otherwise."""
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
            print("  Author: b1329031")
            return True

        if cmd == 'CLEAR':
            os.system('cls' if os.name == 'nt' else 'clear')
            return True

        if cmd == 'NEW':
            if self.modified and not self._confirm_discard():
                return True
            self.buffer   = []
            self.modified = False
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

    # ── program management commands ────────────────────────────────

    def _cmd_append(self):
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
        if new_text:               # empty input → keep original
            self.buffer[n-1] = new_text
            self.modified = True

    def _cmd_delete(self, arg):
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
        try:
            with open(filename, 'w') as f:
                for line in self.buffer:
                    f.write(line + '\n')
            self.modified = False
            print(f"Saved {len(self.buffer)} lines to '{filename}'.")
        except OSError as e:
            print(f"Error: cannot save '{filename}': {e}")

    def _cmd_load(self, filename):
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

    # ── run / check ────────────────────────────────────────────────

    def _cmd_run(self):
        if not self.buffer:
            print("Error: program buffer is empty.")
            return

        code = '\n'.join(self.buffer)
        try:
            defines, clean = extract_defines(code)
            run_interp = self._make_interp(trace=self.interp.trace, defines=defines)
            run_interp._source_lines = self.buffer

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

    # ── funcs ──────────────────────────────────────────────────────

    def _cmd_funcs(self):
        from ast_nodes import FuncDefNode as FDN
        # Collect user functions: prefer buffer (has line numbers) over interactive
        user_funcs = {}   # name -> (FuncDefNode, line_in_buffer)

        # Parse buffer to find function defs with line numbers
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

        # Also include interactively defined functions not in buffer
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

    # ── interactive execution ──────────────────────────────────────

    def _exec_interactive(self, code):
        try:
            defines_new, clean = extract_defines(code)
            self.interp.defines.update(defines_new)

            if not clean.strip():
                return

            tokens = tokenize(clean, self.interp.defines)
            if not tokens:
                return

            stmts = parse_interactive(tokens)
            self.interp.exec_interactive(stmts)

        except ReturnSignal:
            pass  # return at top level is ignored
        except SyntaxError as e:
            print(f"Syntax error: {e}")
        except RuntimeError as e:
            print(f"Runtime error: {e}")
        except SystemExit as e:
            code_val = e.code if e.code is not None else 0
            print(f"Program exited with return value {code_val}.")
        except Exception as e:
            print(f"Error: {e}")

    # ── helpers ────────────────────────────────────────────────────

    def _confirm_discard(self):
        try:
            ans = input("Buffer has unsaved changes. Discard? (y/n): ")
            return ans.strip().lower() in ('y', 'yes')
        except EOFError:
            return True


# ── rough tokenizer for completeness check ─────────────────────────

def _rough_tokenize(code):
    """Return a flat list of token strings for brace/do-while tracking."""
    return re.findall(r'[{}]|[a-zA-Z_]\w*|"[^"]*"|\'[^\']*\'|.', code)


def start():
    REPL().run()
