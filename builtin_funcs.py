# builtin_funcs.py — 內建函式庫
# 職責：向 Interpreter 註冊所有 Small-C 內建函式
# 所有函式以 closure 形式包住 interp，才能存取記憶體（讀寫字串等）
import math, random, sys


def register_builtins(interp):
    """把所有內建函式以 lambda 或 closure 方式注入 interp._builtins dict。

    所有函式的 Python 簽章都是 f(args)，其中 args 是已求值的引數列表（整數）。
    """
    B = interp._builtins

    # ── printf 格式化輸出引擎 ─────────────────────────────────────
    # 獨立為 _do_printf 以便 printf 和未來可能的 sprintf 共用

    def _do_printf(fmt, args):
        """解析格式字串並輸出。
        支援：%d（整數）、%c（字元）、%s（字串，需讀記憶體）、%x（十六進位）、%%（百分號）
        """
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
                # %s 需要從記憶體讀取 null-terminated 字串
                result.append(interp.read_string(int(val)))
            elif spec == 'x':
                result.append(format(int(val) & 0xFFFFFFFF, 'x'))
            elif spec == 'X':
                result.append(format(int(val) & 0xFFFFFFFF, 'X'))
            else:
                result.append(f'%{spec}')
        sys.stdout.write(''.join(result))
        sys.stdout.flush()

    # ── I/O 函式 ──────────────────────────────────────────────────

    def _putchar(args):
        """輸出一個字元（整數 → ASCII 字元）"""
        ch = int(args[0]) & 0xFF
        sys.stdout.write(chr(ch))
        sys.stdout.flush()
        return ch

    def _getchar(args):
        """從標準輸入讀一個字元，遇 EOF 回傳 -1"""
        try:
            ch = sys.stdin.read(1)
            return ord(ch) if ch else -1
        except Exception:
            return -1

    def _puts(args):
        """輸出字串並自動換行（字串地址在 args[0]）"""
        print(interp.read_string(args[0]))
        return 0

    def _printf(args):
        """格式化輸出；args[0] 是格式字串地址，args[1:] 是引數"""
        fmt = interp.read_string(args[0])
        _do_printf(fmt, args[1:])
        return 0

    def _scanf(args):
        """格式化輸入；引數必須是指標（用 & 取址），逐一寫入對應記憶體位址"""
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

    # ── 字串函式 ──────────────────────────────────────────────────

    # strlen：讀字串後取 Python len（不含 null terminator）
    B['strlen'] = lambda a: len(interp.read_string(a[0]))

    def _strcpy(args):
        """把 src 字串複製到 dest，回傳 dest 位址"""
        interp.write_string(args[0], interp.read_string(args[1]))
        return args[0]

    def _strcat(args):
        """把 src 字串接到 dest 字串末尾，回傳 dest 位址"""
        interp.write_string(args[0], interp.read_string(args[0]) + interp.read_string(args[1]))
        return args[0]

    def _strcmp(args):
        """字典序比較：s1 < s2 → -1，s1 == s2 → 0，s1 > s2 → 1"""
        a, b = interp.read_string(args[0]), interp.read_string(args[1])
        return 0 if a == b else (-1 if a < b else 1)

    B['strcpy'] = _strcpy
    B['strcat'] = _strcat
    B['strcmp'] = _strcmp

    # ── 數學函式 ──────────────────────────────────────────────────

    B['abs'] = lambda a: abs(a[0])
    B['max'] = lambda a: max(a[0], a[1])
    B['min'] = lambda a: min(a[0], a[1])

    def _pow(args):
        """整數次方；exp 為負時回傳 0（整數除法的自然結果）"""
        base, exp = args[0], args[1]
        if exp < 0: return 0
        return int(base ** exp)

    def _sqrt(args):
        """整數平方根（向下取整）；負數引數拋出執行期錯誤（加分項目）"""
        if args[0] < 0:
            raise RuntimeError("sqrt() argument must be non-negative")
        return int(math.sqrt(args[0]))

    def _mod(args):
        """整數取餘，等同 % 運算子；b=0 拋出除以零錯誤（加分項目）"""
        a, b = args[0], args[1]
        if b == 0: raise RuntimeError("division by zero")
        return int(a - int(a / b) * b)

    B['pow']   = _pow
    B['sqrt']  = _sqrt
    B['mod']   = _mod
    B['rand']  = lambda a: random.randint(0, 32767)
    B['srand'] = lambda a: (random.seed(a[0]), 0)[-1]

    # ── 記憶體與工具函式 ──────────────────────────────────────────

    def _memset(args):
        """將 ptr 起的 size 個位元組全部設為 value（做 & 0xFF 截斷成位元組）"""
        ptr, value, size = args[0], args[1] & 0xFF, args[2]
        for i in range(size):
            interp.mem.write(ptr + i, value)
        return ptr

    def _atoi(args):
        """字串轉整數；無效字串回傳 0"""
        s = interp.read_string(args[0]).strip()
        try:    return int(s)
        except: return 0

    def _itoa(args):
        """整數轉十進位字串，寫入 str 指標所指的記憶體"""
        interp.write_string(args[1], str(args[0]))
        return args[1]

    def _exit(args):
        """立即終止程式，回傳指定的結束碼（用 Python SystemExit 實作）"""
        raise SystemExit(args[0] if args else 0)

    B['memset']      = _memset
    B['sizeof_int']  = lambda a: 4    # int 固定 4 bytes
    B['sizeof_char'] = lambda a: 1    # char 固定 1 byte
    B['atoi']        = _atoi
    B['itoa']        = _itoa
    B['exit']        = _exit


# ── FUNCS 指令顯示用的簽章列表 ────────────────────────────────────
# 與 C 標準函式庫簽章一致，方便學生對照

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
