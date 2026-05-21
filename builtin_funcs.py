# builtin_funcs.py
import math, random, sys


def register_builtins(interp):
    """Register all built-in functions into interpreter._builtins."""
    B = interp._builtins

    # ── printf engine (closure over interp for %s) ─────────────────

    def _do_printf(fmt, args):
        result = []
        i = 0
        arg_idx = 0
        while i < len(fmt):
            if fmt[i] != '%':
                result.append(fmt[i])
                i += 1
                continue
            i += 1
            if i >= len(fmt):
                result.append('%')
                break
            spec = fmt[i]
            i += 1
            if spec == '%':
                result.append('%')
                continue
            val = args[arg_idx] if arg_idx < len(args) else 0
            arg_idx += 1
            if spec == 'd':
                result.append(str(int(val)))
            elif spec == 'c':
                result.append(chr(int(val) & 0xFF))
            elif spec == 's':
                result.append(interp.read_string(int(val)))
            elif spec == 'x':
                result.append(format(int(val) & 0xFFFFFFFF, 'x'))
            elif spec == 'X':
                result.append(format(int(val) & 0xFFFFFFFF, 'X'))
            else:
                result.append(f'%{spec}')
        sys.stdout.write(''.join(result))
        sys.stdout.flush()

    # ── I/O ───────────────────────────────────────────────────────

    def _putchar(args):
        ch = int(args[0]) & 0xFF
        sys.stdout.write(chr(ch))
        sys.stdout.flush()
        return ch

    def _getchar(args):
        try:
            ch = sys.stdin.read(1)
            return ord(ch) if ch else -1
        except Exception:
            return -1

    def _puts(args):
        print(interp.read_string(args[0]))
        return 0

    def _printf(args):
        fmt = interp.read_string(args[0])
        _do_printf(fmt, args[1:])
        return 0

    def _scanf(args):
        fmt = interp.read_string(args[0])
        count = 0
        arg_idx = 1
        i = 0
        while i < len(fmt) and arg_idx < len(args):
            if fmt[i] == '%' and i + 1 < len(fmt):
                spec = fmt[i + 1]
                try:
                    raw = input()
                    if spec == 'd':
                        interp.mem.write(args[arg_idx], int(raw.strip()))
                        count += 1
                    elif spec == 'c':
                        interp.mem.write(args[arg_idx], ord(raw[0]) if raw else 0)
                        count += 1
                    arg_idx += 1
                except Exception:
                    break
                i += 2
            else:
                i += 1
        return count

    B['putchar'] = _putchar
    B['getchar'] = _getchar
    B['puts']    = _puts
    B['printf']  = _printf
    B['scanf']   = _scanf

    # ── string ────────────────────────────────────────────────────

    B['strlen'] = lambda a: len(interp.read_string(a[0]))

    def _strcpy(args):
        interp.write_string(args[0], interp.read_string(args[1]))
        return args[0]

    def _strcat(args):
        interp.write_string(args[0], interp.read_string(args[0]) + interp.read_string(args[1]))
        return args[0]

    def _strcmp(args):
        a, b = interp.read_string(args[0]), interp.read_string(args[1])
        return 0 if a == b else (-1 if a < b else 1)

    B['strcpy'] = _strcpy
    B['strcat'] = _strcat
    B['strcmp'] = _strcmp

    # ── math ──────────────────────────────────────────────────────

    B['abs'] = lambda a: abs(a[0])
    B['max'] = lambda a: max(a[0], a[1])
    B['min'] = lambda a: min(a[0], a[1])

    def _pow(args):
        base, exp = args[0], args[1]
        if exp < 0: return 0
        return int(base ** exp)

    def _sqrt(args):
        if args[0] < 0:
            raise RuntimeError("sqrt() argument must be non-negative")
        return int(math.sqrt(args[0]))

    def _mod(args):
        a, b = args[0], args[1]
        if b == 0: raise RuntimeError("division by zero")
        return int(a - int(a / b) * b)

    B['pow']   = _pow
    B['sqrt']  = _sqrt
    B['mod']   = _mod
    B['rand']  = lambda a: random.randint(0, 32767)
    B['srand'] = lambda a: (random.seed(a[0]), 0)[-1]

    # ── utility ───────────────────────────────────────────────────

    def _memset(args):
        ptr, value, size = args[0], args[1] & 0xFF, args[2]
        for i in range(size):
            interp.mem.write(ptr + i, value)
        return ptr

    def _atoi(args):
        s = interp.read_string(args[0]).strip()
        try:    return int(s)
        except: return 0

    def _itoa(args):
        interp.write_string(args[1], str(args[0]))
        return args[1]

    def _exit(args):
        raise SystemExit(args[0] if args else 0)

    B['memset']      = _memset
    B['sizeof_int']  = lambda a: 4
    B['sizeof_char'] = lambda a: 1
    B['atoi']        = _atoi
    B['itoa']        = _itoa
    B['exit']        = _exit


# ── FUNCS listing helper ───────────────────────────────────────────

BUILTIN_SIGS = [
    "int putchar(int ch)",
    "int getchar()",
    "void printf(char *fmt, ...)",
    "void puts(char *s)",
    "int scanf(char *fmt, ...)",
    "int strlen(char *s)",
    "void strcpy(char *dest, char *src)",
    "int strcmp(char *s1, char *s2)",
    "void strcat(char *dest, char *src)",
    "int abs(int x)",
    "int max(int a, int b)",
    "int min(int a, int b)",
    "int pow(int base, int exp)",
    "int sqrt(int x)",
    "int mod(int a, int b)",
    "int rand()",
    "void srand(int seed)",
    "void memset(char *ptr, int val, int size)",
    "int sizeof_int()",
    "int sizeof_char()",
    "int atoi(char *s)",
    "void itoa(int val, char *str)",
    "void exit(int code)",
]
