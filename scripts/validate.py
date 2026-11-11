#!/usr/bin/env python3
"""
Antigravity Customization Standards Validator
確定性驗證 Antigravity 各組件（Rules / Agents / Skills / Plugins）語法合規性。
依據 `agy` 二進位逆向規格：
1. 規則檔案大小上限 24,000 bytes (24 KB)。
2. 獨立規則檔嚴禁 `always_on: true`，必須具備合法的 `trigger: always_on | model_decision | glob | manual`。
3. `agent.md` 嚴禁 `enable_write_tools` / `enable_mcp_tools` 等無效標籤，必須顯式宣告 `tools`。
4. Markdown 代理人設正文必須以 `# H1` 分界。
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

VALID_TRIGGERS = {"always_on", "model_decision", "glob", "manual"}
MAX_RULE_SIZE_BYTES = 24000

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def split_frontmatter(content: str) -> Tuple[str, str]:
    """分離 Markdown 前置 YAML Frontmatter 與正文"""
    if content.startswith("---\n") or content.startswith("---\r\n"):
        parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) >= 3:
            return parts[1].strip(), parts[2].strip()
    return "", content.strip()


def parse_simple_yaml(yaml_text: str) -> Dict[str, Any]:
    """解析簡易 YAML（避免強制相依 PyYAML）"""
    try:
        import yaml
        return yaml.safe_load(yaml_text) or {}
    except ImportError:
        pass

    # Zero-dependency fallback parser
    data = {}
    lines = yaml_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            # inline comment stripping
            if "#" in val and not (val.startswith('"') or val.startswith("'")):
                val = val.split("#", 1)[0].strip()
            if val == "true":
                data[key] = True
            elif val == "false":
                data[key] = False
            elif val == "":
                # Could be a list
                items = []
                j = i + 1
                while j < len(lines):
                    sub = lines[j].strip()
                    if sub.startswith("- "):
                        items.append(sub[2:].strip().strip('"').strip("'"))
                        j += 1
                    else:
                        break
                if items:
                    data[key] = items
                    i = j - 1
                else:
                    data[key] = None
            else:
                data[key] = val.strip('"').strip("'")
        i += 1
    return data


def validate_rule_file(path: Path) -> List[str]:
    """驗證單一 Rule 檔案合規性"""
    errors = []
    file_bytes = path.read_bytes()
    size = len(file_bytes)

    # 1. 24 KB 限制
    if size > MAX_RULE_SIZE_BYTES:
        errors.append(f"檔案大小 {size} bytes 超過 agy 硬編碼上限 24,000 bytes (24 KB)")

    content = file_bytes.decode("utf-8", errors="replace")
    filename = path.name

    # 2. AGENTS.md / GEMINI.md 例外
    if filename in ("AGENTS.md", "GEMINI.md"):
        # standalone AGENTS.md 不應包含 frontmatter
        fm, _ = split_frontmatter(content)
        if fm:
            errors.append(f"{filename} 為硬編碼 always_on 規則，不應宣告 YAML Frontmatter")
        return errors

    # 3. 獨立規則檔 Frontmatter 檢查
    fm, body = split_frontmatter(content)
    if not fm:
        errors.append("獨立規則檔缺少 YAML Frontmatter (必須以 `---` 包裹)")
        return errors

    # 檢測非法 always_on: true
    if re.search(r"^\s*always_on\s*:\s*(true|yes)\b", fm, re.IGNORECASE | re.MULTILINE):
        errors.append("嚴禁使用非法語法 `always_on: true`！必須宣告 `trigger: always_on`")

    meta = parse_simple_yaml(fm)

    # 檢測 trigger 欄位
    trigger = meta.get("trigger")
    if not trigger:
        errors.append("缺少 `trigger` 欄位（會被 agy 判定為 Invalid rule trigger: 0 並拋棄）")
    elif trigger not in VALID_TRIGGERS:
        errors.append(f"無效的 trigger: '{trigger}'。必須為 {sorted(list(VALID_TRIGGERS))} 之一")

    # 檢測 model_decision 必須具備 description
    if trigger == "model_decision":
        desc = meta.get("description")
        if not desc or not str(desc).strip():
            errors.append("`trigger: model_decision` 必須具備非空的 `description` 供模型動態路由")

    # 檢測 glob 必須具備 globs
    if trigger == "glob":
        globs = meta.get("globs")
        if not globs:
            errors.append("`trigger: glob` 必須具備 `globs` 欄位")

    return errors


def validate_agent_file(path: Path) -> List[str]:
    """驗證 agent.md 合規性"""
    errors = []
    content = path.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(content)

    if not fm:
        errors.append("agent.md 缺少 YAML Frontmatter")
        return errors

    meta = parse_simple_yaml(fm)

    # 1. 檢測已被棄用的動態參數
    deprecated_fields = ["enable_write_tools", "enable_mcp_tools", "enable_subagent_tools"]
    for f in deprecated_fields:
        if f in meta or re.search(rf"\b{f}\b", fm):
            errors.append(f"發現無效欄位 `{f}`！agent.md 僅支援原生 AgentFrontmatter，請使用 `tools` 陣列與 `inheritMcp`")

    # 2. 檢測 tools 陣列
    tools = meta.get("tools")
    if not tools:
        errors.append("未宣告 `tools` 陣列（底層 agy 將會靜默降級為最小唯讀工具集）")

    # 3. 檢測 System Prompt 必須有 # H1
    h1_match = re.search(r"^#\s+[^\n]+", body, re.MULTILINE)
    if not h1_match:
        errors.append("System Prompt 正文必須以 `# H1` 標題分界")

    return errors


def validate_path(target: Path) -> Tuple[int, int]:
    """驗證路徑下的檔案並統計 (passed, failed)"""
    passed = 0
    failed = 0

    if target.is_file():
        files = [target]
    else:
        files = sorted(list(target.glob("**/*.md")))

    for f in files:
        # 跳過 README 與隱藏目錄
        if f.name.upper() == "README.MD" or ".git" in f.parts:
            continue

        if f.name == "agent.md":
            errs = validate_agent_file(f)
        else:
            errs = validate_rule_file(f)

        rel = f.as_posix()
        if not errs:
            print(f"[{GREEN}PASS{RESET}] {rel}")
            passed += 1
        else:
            print(f"[{RED}FAIL{RESET}] {rel}")
            for e in errs:
                print(f"       {RED}✖{RESET} {e}")
            failed += 1

    return passed, failed


def main():
    paths = sys.argv[1:]
    if not paths:
        # 預設檢查當前目錄下的 format_customizations.md
        default_file = Path("format_customizations.md")
        if default_file.exists():
            paths = [str(default_file)]
        else:
            print(f"{YELLOW}未指定路徑，請提供要驗證的檔案或目錄。{RESET}")
            sys.exit(1)

    total_pass = 0
    total_fail = 0

    print(f"{BLUE}=== Antigravity 規格合規驗證開始 ==={RESET}")
    for p in paths:
        path_obj = Path(p)
        if not path_obj.exists():
            print(f"{RED}路徑不存在: {p}{RESET}")
            total_fail += 1
            continue
        p_count, f_count = validate_path(path_obj)
        total_pass += p_count
        total_fail += f_count

    print(f"\n{BLUE}=== 驗證總結 ==={RESET}")
    print(f"通過: {GREEN}{total_pass}{RESET} | 失敗: {RED if total_fail > 0 else GREEN}{total_fail}{RESET}")

    if total_fail > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
