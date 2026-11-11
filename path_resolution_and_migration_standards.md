---
trigger: model_decision
description: "當處理跨機器、跨使用者遷移、路徑解析、自定義組件 (Rules/Skills/Agents/Hooks/Plugins) 檔案引用、Python 直譯器調用或 Markdown 跨檔案跳轉時觸發。"
---

# 跨環境路徑解析與無縫遷移規範 (Path Resolution & Migration Standards)

本規範統一 Antigravity 體系下所有代碼、腳本、自定義組件（Rules / Skills / Agents / Hooks / Plugins）與 Markdown 文件的檔案路徑解析標準，確保自定義資產與工作流在不同作業系統（Linux / macOS / Windows WSL）、不同使用者帳號（`$USER` / `$HOME`）及不同機器間無縫遷移。

---

### 1. 四層動態路徑解析體系 (Four-Layer Resolution Hierarchy)

所有資源（腳本、組件、設定檔與資料庫）定位必須依序遵循以下四層動態解析協議，嚴禁寫死任何絕對路徑：

```text
Layer 1: 工作區本地優先 (Workspace Local: .agents/...)
   │ └── 若當前專案存在客製化版本，優先載入
   ▼
Layer 2: 外掛套件根目錄 (Plugin Root Resolution)
   │ └── 判定 .agents/plugins/<pkg> 或 ~/.gemini/config/plugins/<pkg>
   ▼
Layer 3: 全域配置底座 (Global Base: ~/.gemini/config/...)
   │ └── 動態展開 $HOME / Path.home()，作為全域通用回退
   ▼
Layer 4: Python 直譯器透明鏈 (Interpreter Resolution Chain)
     └── pre_tool_use_hook 自動攔截注入：Workspace .venv > 全域 venv > python3
```

---

### 2. 嚴禁硬編碼使用者路徑與個人標籤 (Zero Personal Paths)

1. **嚴禁任何個人帳號或絕對路徑**：
   - 程式碼、設定檔、`SKILL.md` 與文件嚴禁出現 `/home/<user>/`、`/Users/<user>/`、`C:\Users\<user>\` 或固定 IP。
   - 文件範例或防呆說明僅允許使用泛型代稱（如 `/home/username/...`、`~/.gemini/...`）。
2. **標準三階動態解析順序**：
   - **第一階 (CLI Flag)**：顯式傳入之引數（如 `--app-data-dir`、`--config-path`）。
   - **第二階 (Environment Variable)**：環境變數（如 `ANTIGRAVITY_CONFIG_DIR`、`VIRTUAL_ENV`、`WORKSPACE_ROOT`）。
   - **第三階 (Dynamic Discovery)**：標準函式動態推導（`Path.home()`、`Path(__file__).resolve().parent`、`os.path.expanduser("~")`）。

---

### 3. 標準程式碼與腳本實作樣板 (Standard Templates)

#### A. Python 動態模組與路徑推導
```python
from pathlib import Path
import os

# 1. 取得當前腳本所在的自包含目錄
CURRENT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = CURRENT_DIR.parent if (CURRENT_DIR.parent / "plugin.json").exists() else CURRENT_DIR

# 2. 跨層級動態解析組件路徑 (專案優先，全域回退)
def resolve_customization_path(subpath: str) -> Path:
    workspace_target = Path.cwd() / ".agents" / subpath
    if workspace_target.exists():
        return workspace_target
    return Path.home() / ".gemini" / "config" / subpath
```

#### B. Shell / `SKILL.md` 雙層解析與直譯器調用
在 Skill 指令區塊中，**嚴禁寫死特定虛擬環境路徑**（如 `~/gemini_py3_env/bin/python`）。直接調用 `python3`，依託全域 `pre_tool_use_hook.py` 自動轉導至當前最合適的直譯器：

```bash
# 1. 獨立解析外掛或技能路徑 (專案優先，全域回退)
PLUGIN_ROOT="$([ -d .agents/plugins/<plugin-name> ] && echo .agents/plugins/<plugin-name> || echo ~/.gemini/config/plugins/<plugin-name>)"
SCRIPT_PATH="$PLUGIN_ROOT/skills/<skill-name>/scripts/<script>.py"

# 2. 直接以 python3 執行 (由生命週期自動化鉤子負責環境轉導)
python3 "$SCRIPT_PATH" "$@"
```

#### C. 外掛生命週期鉤子 (`hooks.json`)
外掛內部註冊的鉤子命令必須使用相對路徑與標準直譯器：
```json
{
  "plugin-hook": {
    "enabled": true,
    "SessionStart": [
      {
        "type": "command",
        "command": "python3 ./hooks/session_start.py",
        "timeout": 10
      }
    ]
  }
}
```

---

### 4. 檔案引用與 Markdown 跨層鏈結邊界 (Markdown & Link Boundaries)

1. **嚴禁逃逸跨倉庫相對路徑**：
   - 每個獨立 Repository（如 `antigravity-rules`、`antigravity-skills`、外掛套件）必須自成一體（Self-contained）。
   - 嚴禁在 Markdown 文件中使用跳出倉庫邊界的相對路徑（例如 `../../skills/foo/SKILL.md` 或 `../plugins/bar/`）。
2. **對話舉證與報告說明層（Chat & Artifact Citations）**：
   - 為防止 Antigravity UI 將 `[text](file:///...)` 強制縮減為純檔名（basename），向使用者舉證檔案時，**必須以獨立行內代碼 `` `完整路徑` `` 顯示於 `file://` 連結之外**：
     - **工作區內檔案**：顯示相對於工作區根目錄之相對路徑，格式：``.agents/rules/AGENTS.md`` ([🔗](file:///abs/path/.agents/rules/AGENTS.md))。
     - **工作區外檔案**：顯示執行期解析後之完整絕對路徑，格式：``~/.gemini/config/rules/AGENTS.md`` ([🔗](file:///abs/path/to/AGENTS.md))。

---

### 5. 跨環境遷移檢查清單 (Migration Checklist)

當將 Antigravity 配置遷移至新機器、新使用者或新容器時，執行以下三步驗收：

1. **基礎目錄就位**：執行各倉庫內附之 `./install.sh --global`，自動建立軟連結或複製至 `~/.gemini/config/`。
2. **直譯器自動感應**：確保終端或專案具有可用之 Python 3 環境（如 `.venv` 或系統 `python3`）。`pre_tool_use_hook.py` 會自動接管環境變數。
3. **規範自檢通過**：於各組件目錄執行對應之驗證器（如 `python scripts/validate_rules.py .`），確認零硬編碼錯誤。
