#!/bin/zsh
# Ritual File Renamer - 一鍵啟動腳本
# 雙擊此檔案即可啟動應用程式

# 切換到腳本所在目錄
cd "$(dirname "$0")"

echo ""
echo "🕯️ 法事檔案自動配對命名工具"
echo "=============================="
echo ""

# ===== 檢查 Python =====
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo "✅ Python: $PYTHON_VERSION"
        return 0
    else
        return 1
    fi
}

install_python_guide() {
    echo ""
    echo "❌ 未偵測到 Python 3"
    echo ""
    echo "請依照以下步驟安裝："
    echo ""
    echo "  方法 1：使用 Homebrew（推薦）"
    echo "  ─────────────────────────────"
    echo "  1. 開啟「終端機」應用程式"
    echo "  2. 貼上以下指令安裝 Homebrew："
    echo ""
    echo '     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    echo "  3. 安裝完成後，執行："
    echo ""
    echo "     brew install python@3.11 tesseract tesseract-lang ffmpeg"
    echo ""
    echo "  4. 重新雙擊 start.command 即可"
    echo ""
    echo "  ─────────────────────────────"
    echo "  方法 2：從官網下載"
    echo "  ─────────────────────────────"
    echo "  前往 https://www.python.org/downloads/ 下載安裝"
    echo ""
    echo "按 Enter 關閉..."
    read
    exit 1
}

# ===== 檢查系統依賴 =====
check_dependencies() {
    local missing=()
    
    if ! command -v tesseract &> /dev/null; then
        missing+=("tesseract")
    else
        echo "✅ Tesseract OCR: $(tesseract --version 2>&1 | head -1)"
    fi
    
    if ! command -v ffprobe &> /dev/null; then
        missing+=("ffmpeg")
    else
        echo "✅ ffmpeg: $(ffprobe -version 2>&1 | head -1 | cut -d' ' -f3)"
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo ""
        echo "⚠️ 缺少以下系統依賴："
        for dep in "${missing[@]}"; do
            echo "   • $dep"
        done
        echo ""
        echo "請執行以下指令安裝："
        echo ""
        echo "   brew install ${missing[*]} tesseract-lang"
        echo ""
        echo "按 Enter 繼續（部分功能可能無法使用）..."
        read
    fi
}

# ===== 主程式 =====

# 檢查 Python
if ! check_python; then
    install_python_guide
fi

# 檢查系統依賴
check_dependencies

echo ""

# 檢查並建立虛擬環境
if [ ! -d "venv" ]; then
    echo "📦 首次執行，正在建立虛擬環境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 建立虛擬環境失敗"
        echo "按 Enter 關閉..."
        read
        exit 1
    fi
    echo "✅ 虛擬環境建立完成"
fi

# 啟動虛擬環境
source venv/bin/activate

# 安裝/更新依賴
echo "📦 檢查 Python 套件..."
pip install -r requirements.txt -q --upgrade
echo "✅ 套件安裝完成"

echo ""
echo "🚀 啟動應用程式..."
echo ""

# 啟動 GUI
python gui.py

# 如果發生錯誤，保持視窗開啟
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 程式發生錯誤"
    echo "按 Enter 關閉..."
    read
fi
