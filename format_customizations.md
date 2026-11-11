---
trigger: model_decision
description: "當建立、修改或重構 Antigravity 自定義組件（Rules 行為約束、Skills 技能腳本、Agents 子代理人設、Hooks 生命週期鉤子、Plugins 套件）時調用，以確保檔案擺放位置、優先級、雙級觸發鏈與 YAML 語法合規。"
---

# Antigravity 自定義系統格式與架構標準 (Customization Standards)

本規範統一規範 Antigravity 體系五大核心自定義組件（Rules / Skills / Agents / Hooks / Plugins）之檔案放置路徑、優先級覆蓋、職責邊界與 YAML Frontmatter 防呆標準。

---

### 1. 雙層檔案路徑架構 (Global vs Workspace)

所有自定義組件均嚴格遵循「**工作區本地優先，全域回退（Workspace Overrides Global）**」與「**預先安裝就緒 + 原生漸進式觸發（Progressive Disclosure，零 Cold Start）**」機制：

| 組件類型 | 全域路徑 (Global - 本機所有專案通用底座) | 工作區路徑 (Workspace - 當前專案優先) |
| :--- | :--- | :--- |
| **Rules (行為約束)** | `~/.gemini/config/rules/*.md`<br>`~/.gemini/config/rules/AGENTS.md` | `.agents/rules/*.md`<br>`.agents/rules/AGENTS.md` (或 `<root>/AGENTS.md`) |
| **Skills (技能與腳本)** | `~/.gemini/config/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` (或 `.agents/skills.json`) |
| **Agents (子代理人設)** | `~/.gemini/config/agents/<name>/agent.md` | `.agents/agents/<name>/agent.md` |
| **Hooks (生命週期鉤子)** | `~/.gemini/config/hooks.json` | `.agents/hooks.json` |
| **Plugins (命名空間套件)** | `~/.gemini/config/plugins/<name>/plugin.json` | `.agents/plugins/<name>/plugin.json` (或 `.agents/plugins.json`) |

#### 標準雙層目錄結構樹
```text
├── 全域通用配置 (~/.gemini/config/)          # 所有專案通用底座
│   ├── rules/                              # 全域通用安全與環境約束
│   │   ├── AGENTS.md                       # 全域常駐總則 (Always-on, 無 Frontmatter)
│   │   └── <rule-name>.md                  # 全域領域規範 (trigger: model_decision / glob)
│   ├── skills/                             # 全域通用原子工具庫
│   ├── agents/                             # 全域預設子代理人設
│   ├── hooks.json                          # 全域生命週期自動化
│   └── plugins/                            # 跨專案通用外掛套件
│
└── 專案本地配置 (<project_root>/.agents/)     # 當前專案優先覆蓋
    ├── rules/                              # 專案特定業務規範 (*.md)
    │   ├── AGENTS.md                       # 專案常駐總則 (Always-on, 無 Frontmatter)
    │   └── <rule-name>.md                  # 專案特定領域規範 (trigger: model_decision / glob)
    ├── skills/                             # 專案專用腳本工具
    ├── agents/                             # 專案客製化專業工位
    ├── hooks.json                          # 專案防禦與自動化鉤子
    └── plugins/                            # 專案專用套件 (或 plugins.json)
```

---

### 2. 規則雙軌體系與 YAML / JSON 語法約束

#### A. 規則檔雙軌解析機制 (`AGENTS.md` vs `rules/<name>.md`)
依據底層 Go 引擎（`parseRuleInfo`）解析邏輯，無論全域（`~/.gemini/config/rules/`）、專案本地（`.agents/rules/`）或外掛（`plugins/<name>/rules/`），規則檔案均遵循確定性雙軌分支：

1. **特權常駐規則 (`rules/AGENTS.md` 或 `GEMINI.md`)**：
   - **底層分支**：直接跳過 Frontmatter 解析器（`SplitMarkdownFrontmatter`），硬編碼強制為 `trigger: always_on`。
   - **語法約束**：純 Markdown 正文，**嚴禁/忽略** YAML Frontmatter。
   - **核心用途**：定義專案或外掛的全局 SOP、開發總方針與團隊共識，對話全程常駐。
2. **一般自定義規則 (`rules/<name>.md`，非 `AGENTS.md` / `GEMINI.md` 之任意 `.md` 檔)**：
   - **底層分支**：強制解析 YAML Frontmatter，並依 `trigger` 枚舉進行分類（`categorizeRule`）。
   - **語法約束**：**必須**宣告合法 `trigger:`（值嚴格限定為 `always_on`、`model_decision`、`glob`、`manual` 四種），**嚴禁使用 `always_on: true`**（此為非法語法，會觸發 `Invalid rule trigger: 0` 導致規則被靜默拋棄）。
   - **特殊檔名例外**：若於 `rules/` 內放置無 Frontmatter 的 `README.md`，底層會自動將其視為說明檔並靜默跳過（skip），不參與模型推理。

#### B. `RuleFrontmatter` 結構體與 4 種 Trigger 完整規格
經逆向 `agy` 核心結構體 `customizations.RuleFrontmatter`：
```go
type RuleFrontmatter struct {
    Trigger     string `yaml:"trigger"`
    Description string `yaml:"description"`
    Glob        string `yaml:"glob"`
    Globs       string `yaml:"globs"` // 底層雙相容 glob 與 globs
}
```

底層 `categorizeRule` 僅支援以下 4 種合法 Trigger（缺省或超出枚舉範圍均直接拋棄）：

1. **`always_on`（常駐全域規則）**：
   - 無條件常駐，參與 20,000 Tokens 專用預算結算。
   ```yaml
   ---
   trigger: always_on
   ---
   ```
2. **`model_decision`（語意按需動態觸發）**：
   - 平時僅向上下文注入一行摘要，當任務意圖匹配時由模型自主掛載全文。
   - **必須具備 `description:` 欄位**（缺省會引發 CLI 警告）。
   ```yaml
   ---
   trigger: model_decision
   description: "當處理資料庫 Schema 變更、SQL 遷移或索引優化時觸發載入"
   ---
   ```
3. **`glob`（檔案路徑模式匹配）**：
   - 當 Agent 讀取、編輯符合萬用字元特徵的檔案時自動掛載全文。
   - **必須具備 `globs:` 或 `glob:` 欄位**（缺省會引發 CLI 警告）。支援逗號分隔、大括號展開與路徑前綴：
   ```yaml
   ---
   trigger: glob
   globs: "**/*.{ts,tsx}, **/frontend/**"
   description: "前端 TypeScript 靜態型別與組件規範"
   ---
   ```
4. **`manual`（純手動提及觸發）**：
   - 平時完全不注入上下文，亦不參與模型自動決策，僅供手動工作流或使用者顯式提及時查閱。
   ```yaml
   ---
   trigger: manual
   description: "緊急災難還原手冊與資料庫回滾流程（僅供手動參照）"
   ---
   ```

---

#### C. 技能描述檔 (`skills/<name>/SKILL.md`)
`SKILL.md` 必須具備 `name` 與明確的原子動作 `description`，供系統進行動態語意檢索與漸進式掛載（Progressive Disclosure）：
```yaml
---
name: <skill-name>
description: "明確的原子操作動詞、CLI 腳本名稱與目標檔案副檔名特徵（充當原子工具箱 Atomic Action）"
---
```
**腳本雙層動態解析與統一環境防衝突**：
Skill 中的腳本嚴禁寫死個人絕對路徑，必須支援專案本地優先的動態切換，直譯器調用請參閱 [跨環境路徑解析與無縫遷移規範](path_resolution_and_migration_standards.md)：
```bash
SCRIPT_PATH="$([ -f .agents/skills/<name>/scripts/<script>.py ] && echo .agents/skills/<name>/scripts/<script>.py || echo ~/.gemini/config/skills/<name>/scripts/<script>.py)"
python3 "$SCRIPT_PATH" ...
```

---

#### D. 子代理人設檔 (`agents/<name>/agent.md`)
經逆向查驗 `agy` 二進位實作（`customizations.AgentFrontmatter` 與 `customizations.saveMDAgent`），`enable_write_tools`、`enable_mcp_tools`、`enable_subagent_tools` 僅為動態工具 `define_subagent` 的 JSON 調用參數，**並非 `agent.md` 支援的 YAML Frontmatter 鍵名**（寫入 YAML 會被 `yaml.Unmarshal` 靜默丟棄，且省略 `tools` 時底層僅掛載唯讀預設集）。
靜態 `agent.md` 必須使用 `AgentFrontmatter` 原生結構標籤顯式宣告 `tools` 陣列與 `inheritMcp`（System Prompt 正文須以 `# H1` 標題開頭）：
```yaml
---
name: <agent-name>
description: "人設與職責描述"
model: pro           # pro (深度推理/文學潤飾), flash (高速對齊/邊界測試), flash_lite, 或 inherit
subagent: true       # 啟用時底層自動注入 send_message 工具，無需手動列出
mainAgent: false     # 設為 false 可從 /agents 與 agy agents 清單隱藏純背景工人以保持介面整潔；若省略則預設為 true（可供使用者在 CLI 獨立啟動調試）
inheritMcp: false    # 對應 EnableMCPTools: false
tools:               # 省略時僅掛載唯讀預設集；必須依角色最小權限顯式列出所需工具以支援帶外日誌落盤
  - read_file        # 註：view_file 與 read_file 解析為同一工具，切勿同時填入以免觸發 tool name conflict
  - write_file
  - edit_file        # 純顧問型（如 architect / redteam）應省略 edit_file
  - run_command
  - manage_task
  # 按需選配：search_web, schedule, generate_image
  # 葉節點工位嚴禁於 tools 列入 define_subagent / invoke_subagent / manage_subagents，防止未授權遞迴衍生
---
```
*(註：對純顧問型子代理如 `architect` / `redteam`，於其 System Prompt 中規範寫入路徑白名單僅限 `.agents/logs/` 與 `.agents/scratchpad/`，嚴禁修改專案業務源碼。)*

---

#### E. 官方插件套件 (`plugins/<name>/plugin.json`)
當需要將同一服務或領域的 `skills/`、`agents/`、`rules/`、`hooks.json` 與 `mcp_config.json` 打包為單一可啟停/分發的單元時，**必須使用 Antigravity 官方 Plugin 結構，嚴禁自造 `blueprints/` 等非標準目錄**。
Plugin 內的 `rules/AGENTS.md` 自動常駐，其餘 `rules/*.md` 需依上述 A/B 節配置 Frontmatter。

---

### 3. 五位一體職責解耦鐵律 (Separation of Concerns)

為杜絕組件職能混淆、規則膨脹與能力丟失，所有設計必須嚴格堅守本質分工：

1. **Rule = 政策/領域路由器/驗收標準/專案工作流（What / Router, Constraint & Workflow）**：
   - Global Rules 定義系統邊界、硬體規格標準、調度方針與交付品質驗收門檻，以及按需觸發的領域規範（`trigger: model_decision`）。
   - Workspace `.agents/rules/AGENTS.md` 定義**該特定 Project 的階段式標準作業流程（Project SOP & Stage Gates）**。
   - 純政策與調度流程文字，**不包含易變的具體 Python 實作腳本**。
2. **Skill = 實體工具庫/SDK/原子動作（How / Atomic Toolkit）**：
   - 封裝可執行的 Python/Bash 腳本、演算法庫、CLI 工具與單元測試。
   - 預先安裝就緒，透過 Progressive Disclosure 按需調用（0 Cold Start），具備自包含性（Self-contained），**嚴禁在測試中寫死外部路徑或專案特定檔案**。
3. **Agent = 專業葉節點工位/口吻/寫入邊界（Who / Leaf Specialist）**：
   - 定義專業角色口吻（如架構師、紅隊、初翻員、文學總監）與帶外落盤輸出協議。
4. **Hook (`hooks.json`) = 生命週期確定性自動化（When / Lifecycle Guardrail）**：
   - 在 `SessionStart`、`PreToolUse`、`Stop` 等事件點自動執行交接檢測、專案 Profile 注入與防呆攔截，實現零注意力消耗。
5. **Plugin (`plugin.json`) = 命名空間套件容器（Where / Namespaced Bundle）**：
   - 官方標準封裝容器，用於整合特定外部服務或子系統的 Skills、Agents、Rules、Hooks 與 MCP Server。

---

### 4. 零能力遺漏重構鐵律 (Zero Feature Loss Mandate)

在對既有架構進行精簡、重構或解耦時，必須無條件遵循以下防護鐵律：

- **前置實裝與測試閉環**：
  從 Rule 中剝離操作細節或演算法的前提，是該細節**已在 Skill 中轉化為經過單元測試（Unit Test）100% 覆蓋的實體程式碼**！嚴禁在 Skill 尚未實裝前逕行刪減 Rule，杜絕架構知識與防線永久蒸發。
- **使用者審閱確認閘門 (Human-in-the-Loop Gate)**：
  任何涉及全域組件刪改、規則瘦身或架構重組，必須先向使用者列出變更對比清單，經明確授權後方可執行。
