# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 啟動與執行

```bash
python3 main.py          # 啟動互動式 REPL
python3 main.py < input  # 非互動式管線輸入
```

測試單一 `.sc` 檔：
```bash
python3 main.py << 'EOF'
LOAD tests/test05_fibonacci.sc
RUN
QUIT
EOF
```

不需要編譯，不需要第三方套件，Python 3.10+ 即可。

## 整體架構

資料流：原始碼 → lexer → tokens → parser → AST → interpreter

**`lexer.py`** — `tokenize(code, defines)` 先呼叫 `strip_comments`，再用 regex 比對 token。`extract_defines` 在 tokenize 前抽出所有 `#define` 行；`apply_defines` 做整字替換。Token type 包含 `KW`、`ID`、`NUMBER`、`STRING`、`CHAR` 與各運算子。

**`ast_nodes.py`** — 純資料類別，無方法。每種陳述式與表達式各有獨立節點。`AssignNode(target, op, value)`：op 為 `'='` 表示單純指定，`'+'`/`'-'` 等表示複合指定（`+=`）。`SwitchNode` 持有 `(value_node, [stmts])` 串列與 `default_stmts`。

**`parser.py`** — 遞迴下降，13 層運算子優先序（`_parse_assign` → … → `_parse_primary`）。`parse_program()` 處理完整檔案；`parse_interactive(tokens)` 處理 REPL 輸入（同時支援陳述式與頂層函式定義）。每個節點會被設上 `._line` 供 TRACE 顯示用。

**`interpreter.py`** — `Memory` 是 dict 形式的位址空間（`alloc(size)` 回傳 base address）。`Scope(parent)` 串接語彙作用域幀，每個變數條目為 `{'addr', 'type', 'size'}`。控制流程以例外實作：`ReturnSignal`、`BreakSignal`、`ContinueSignal`。`_call_depth` 決定 TRACE 縮排（`indent = '  ' * max(0, self._call_depth - 1)`）。**指標關鍵規則**：`info['size'] == 1` 表示純量/指標，索引時用 `mem.read(info['addr'])` 取得 base；`size > 1` 才是真正的陣列，直接用 `info['addr']` 作為 base。

**`builtin_funcs.py`** — `register_builtins(interp)` 以 closure 填入 `interp._builtins` dict。`BUILTIN_SIGS` 是 `FUNCS` 指令顯示用的簽章列表。

**`repl.py`** — `REPL` 持有行緩衝區（`self.buffer`）、一個持久的 `Interpreter`、以及 `modified` 旗標。`_cmd_run()` 每次 RUN 建立**全新** `Interpreter`（重置全域狀態），但會複製 `_source_lines = self.buffer` 供 TRACE 查找行號。`_is_complete(code)` 計算大括號深度，決定要顯示續行提示 `  >` 還是立即執行。`_cmd_funcs()` 重新解析緩衝區以取得含行號的 `FuncDefNode`。

## 關鍵不變式

- Parser 裡的 `++`/`--` 必須用 `op='='` 而非 `op='+'`。用 `'+'` 會造成 `i = i + (i+1)` 的雙重加法 bug。
- `extract_defines` 移除 `#define` 行時不補空行，導致 parser 行號比緩衝區行號少（每個 `#define` 少 1）。FUNCS 顯示的行號因此與 LIST 看到的行號有些微差異，這是預期行為。
- 用 zsh `echo` 管線測試時，`\n` 會被解讀為真實換行。含跳脫序列的輸入請改用 heredoc（`<< 'EOF'`）。
