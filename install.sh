#!/usr/bin/env bash
#
# Antigravity Customization Standards Installer
# 一鍵部署 format_customizations.md 規範至本機全域或專案工作區
#
# 用法:
#   全域安裝 (預設 ~/.gemini/config/rules/):
#     curl -fsSL https://raw.githubusercontent.com/shiroiyuki/antigravity_format_rule/main/install.sh | bash
#
#   工作區安裝 (當前專案 ./.agents/rules/):
#     curl -fsSL https://raw.githubusercontent.com/shiroiyuki/antigravity_format_rule/main/install.sh | bash -s -- --workspace
#

set -euo pipefail

# ANSI 顏色
GREEN="\033[92m"
YELLOW="\033[93m"
BLUE="\033[94m"
RED="\033[91m"
RESET="\033[0m"

REPO_RAW_URL="https://raw.githubusercontent.com/shiroiyuki/antigravity_format_rule/main"
FILES=("format_customizations.md" "path_resolution_and_migration_standards.md")

MODE="global"

for arg in "$@"; do
    case "$arg" in
        -w|--workspace)
            MODE="workspace"
            ;;
        -g|--global)
            MODE="global"
            ;;
        -h|--help)
            echo "Antigravity Customization Standards Installer"
            echo "Usage: install.sh [OPTIONS]"
            echo "Options:"
            echo "  -g, --global     安裝至全域底座 ~/.gemini/config/rules/ (預設)"
            echo "  -w, --workspace  安裝至當前工作區 ./.agents/rules/"
            echo "  -h, --help       顯示此說明"
            exit 0
            ;;
        *)
            echo -e "${YELLOW}未知參數: $arg，將忽略${RESET}"
            ;;
    esac
done

if [ "$MODE" = "workspace" ]; then
    TARGET_DIR=".agents/rules"
    DISPLAY_NAME="專案工作區 (.agents/rules/)"
else
    TARGET_DIR="${HOME}/.gemini/config/rules"
    DISPLAY_NAME="全域底座 (~/.gemini/config/rules/)"
fi

echo -e "${BLUE}=== 安裝 Antigravity 自定義格式標準 ===${RESET}"
echo -e "目標位置: ${YELLOW}${DISPLAY_NAME}${RESET}"

# 建立目標目錄
mkdir -p "$TARGET_DIR"

# 判斷是否在本地 repo 執行
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

for FILE_NAME in "${FILES[@]}"; do
    TARGET_FILE="${TARGET_DIR}/${FILE_NAME}"
    if [ -n "$SCRIPT_DIR" ] && [ -f "${SCRIPT_DIR}/${FILE_NAME}" ]; then
        echo -e "從本地儲存庫複製 ${FILE_NAME} ..."
        cp "${SCRIPT_DIR}/${FILE_NAME}" "$TARGET_FILE"
    else
        echo -e "從 GitHub 下載 ${FILE_NAME} ..."
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL "${REPO_RAW_URL}/${FILE_NAME}" -o "$TARGET_FILE"
        elif command -v wget >/dev/null 2>&1; then
            wget -qO "$TARGET_FILE" "${REPO_RAW_URL}/${FILE_NAME}"
        else
            echo -e "${RED}錯誤: 系統未安裝 curl 或 wget，無法下載檔案。${RESET}" >&2
            exit 1
        fi
    fi

    # 驗證下載檔案大小與完整性
    if [ ! -s "$TARGET_FILE" ]; then
        echo -e "${RED}錯誤: 安裝檔案 ${FILE_NAME} 為空或建立失敗。${RESET}" >&2
        exit 1
    fi

    FILE_SIZE=$(wc -c < "$TARGET_FILE")
    echo -e "${GREEN}✔ 安裝成功！${RESET} ${FILE_NAME} (${FILE_SIZE} bytes)"
    echo -e "檔案路徑: ${GREEN}${TARGET_FILE}${RESET}"
done
echo -e "\n${BLUE}使用說明:${RESET}"
echo -e "當前對話或專案開啟時，Antigravity 會在處理自定義組件（Rules / Skills / Agents / Hooks / Plugins）時自動路由並掛載此標準。"
