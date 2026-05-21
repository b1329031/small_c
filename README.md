# Small-C 互動式解譯器

2026 春季學期 系統軟體 期末專題 — b1329031

以 Python 3 實作的 Small-C（C 語言子集）樹狀走訪解譯器，提供互動式 REPL 與程式緩衝區管理功能。

## 環境需求

- Python 3.10 以上
- 不需任何第三方套件

## 啟動方式

```bash
python3 main.py
```

## REPL 指令

| 指令 | 說明 |
|---|---|
| `APPEND` | 將一行加入程式緩衝區 |
| `LIST` | 顯示目前緩衝區（含行號） |
| `EDIT n` | 取代第 n 行 |
| `DELETE n` | 刪除第 n 行 |
| `INSERT n` | 在第 n 行前插入一行 |
| `NEW` | 清空緩衝區 |
| `SAVE 檔名` | 將緩衝區存檔 |
| `LOAD 檔名` | 從檔案載入到緩衝區 |
| `RUN` | 執行緩衝區程式 |
| `TRACE` | 逐行追蹤執行（含縮排顯示呼叫深度） |
| `CHECK` | 僅做語法檢查，不執行 |
| `VARS` | 顯示目前所有變數值 |
| `FUNCS` | 列出已定義的函式 |
| `HELP` | 顯示所有指令說明 |
| `QUIT` / `EXIT` | 離開解譯器 |

也可在提示符號後直接輸入單行 Small-C 敘述立即執行。

## 支援的語言特性

**型別：** `int`、`char`、`void`、`int*`、`char*`

**控制結構：** `if`/`else`、`while`、`for`、`do`/`while`、`switch`/`case`/`default`、`break`、`continue`、`return`

**運算子：** 完整的 C 語言算術、位元、關係、邏輯、指定運算子，包含複合指定（`+=`、`-=` 等）與遞增/遞減（`++`、`--`）

**陣列與指標：** 一維陣列、取址（`&`）、解參考（`*`）、指標參數傳遞

**前處理：** `#define` 常數替換、`//` 與 `/* */` 註解、十六進位常數（`0x…`）

**內建函式：**
- 輸出入：`printf`、`scanf`
- 數學：`abs`、`sqrt`、`pow`、`max`、`min`
- 字串：`strlen`、`strcpy`、`strcat`、`strcmp`、`strncpy`
- 工具：`rand`、`srand`、`exit`、`sizeof_int`、`sizeof_char`

## 檔案結構

```
main.py          程式入口
lexer.py         詞法分析（strip_comments、extract_defines、tokenize）
ast_nodes.py     全套 AST 節點類別
parser.py        遞迴下降解析器（13 層運算子優先序）
interpreter.py   樹狀走訪解譯器（Memory、Scope、call stack）
builtin_funcs.py 內建函式註冊表
repl.py          REPL 與緩衝區管理
symtable.py      保留存根（已由 Scope 取代）
tests/           10 個測試程式及對應的預期輸出檔
```

## 測試檔說明

| 檔案 | 測試內容 |
|---|---|
| `test01_arithmetic.sc` | 算術運算子、`#define`、複合指定、十六進位常數 |
| `test02_variables.sc` | `char` 型別、位元運算、`abs`/`sqrt`/`pow` |
| `test03_if_else.sc` | `if`/`else`/`else-if`、`switch`/`case`/`default` |
| `test04_loops.sc` | `while`、`for`、`do`/`while`、`break`、`continue` |
| `test05_fibonacci.sc` | 遞迴費氏數列 |
| `test06_functions.sc` | `factorial`、`gcd`、`is_even`（多函式互呼） |
| `test07_arrays.sc` | 一維陣列、`strcpy`/`strcat`/`strlen` 字串操作 |
| `test08_pointers.sc` | 指標傳遞（`swap`）、以指標參數操作陣列 |
| `test09_error_divzero.sc` | 執行期錯誤：除以零 |
| `test10_error_bounds.sc` | 執行期錯誤：陣列索引超出範圍 |
