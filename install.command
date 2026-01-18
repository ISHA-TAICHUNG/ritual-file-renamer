#!/bin/bash

# ============================================
# 法事檔案自動配對命名工具 - 安裝腳本
# ============================================

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     法事檔案自動配對命名工具 - 安裝程式                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 取得腳本所在目錄
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 檢查是否為 Apple Silicon
if [[ $(uname -m) == "arm64" ]]; then
    BREW_PATH="/opt/homebrew/bin/brew"
    BREW_PREFIX="/opt/homebrew"
else
    BREW_PATH="/usr/local/bin/brew"
    BREW_PREFIX="/usr/local"
fi

# ============================================
# 步驟 1: 安裝 Homebrew
# ============================================
echo "📦 步驟 1/4: 檢查 Homebrew..."

if command -v brew &> /dev/null || [ -f "$BREW_PATH" ]; then
    echo "✅ Homebrew 已安裝"
    # 確保 brew 在 PATH 中
    eval "$($BREW_PATH shellenv)" 2>/dev/null
else
    echo "⏳ 正在安裝 Homebrew（需要輸入密碼）..."
    echo ""
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # 設定 Homebrew 路徑
    if [ -f "$BREW_PATH" ]; then
        eval "$($BREW_PATH shellenv)"
        echo 'eval "$('$BREW_PATH' shellenv)"' >> ~/.zprofile
        echo "✅ Homebrew 安裝完成"
    else
        echo "❌ Homebrew 安裝失敗，請手動安裝"
        read -p "按 Enter 結束..."
        exit 1
    fi
fi

echo ""

# ============================================
# 步驟 2: 安裝 Tesseract OCR
# ============================================
echo "📦 步驟 2/4: 檢查 Tesseract OCR..."

if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract 已安裝"
else
    echo "⏳ 正在安裝 Tesseract..."
    brew install tesseract tesseract-lang
    if command -v tesseract &> /dev/null; then
        echo "✅ Tesseract 安裝完成"
    else
        echo "❌ Tesseract 安裝失敗"
    fi
fi

echo ""

# ============================================
# 步驟 3: 安裝 FFmpeg
# ============================================
echo "📦 步驟 3/4: 檢查 FFmpeg..."

if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg 已安裝"
else
    echo "⏳ 正在安裝 FFmpeg..."
    brew install ffmpeg
    if command -v ffmpeg &> /dev/null; then
        echo "✅ FFmpeg 安裝完成"
    else
        echo "❌ FFmpeg 安裝失敗"
    fi
fi

echo ""

# ============================================
# 步驟 4: 安裝 Python 套件
# ============================================
echo "📦 步驟 4/4: 安裝 Python 套件..."

# 檢查 requirements.txt 是否存在
if [ -f "requirements.txt" ]; then
    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install -r requirements.txt --quiet
    echo "✅ Python 套件安裝完成"
else
    echo "❌ 找不到 requirements.txt"
fi

echo ""

# ============================================
# 安裝完成
# ============================================
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    安裝完成檢查                             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 最終檢查
ALL_OK=true

if command -v brew &> /dev/null; then
    echo "✅ Homebrew: $(brew --version | head -1)"
else
    echo "❌ Homebrew: 未安裝"
    ALL_OK=false
fi

if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract: $(tesseract --version 2>&1 | head -1)"
else
    echo "❌ Tesseract: 未安裝"
    ALL_OK=false
fi

if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"
else
    echo "❌ FFmpeg: 未安裝"
    ALL_OK=false
fi

if python3 -c "import pytesseract; import cv2; import PIL; import customtkinter" 2>/dev/null; then
    echo "✅ Python 套件: 已安裝"
else
    echo "❌ Python 套件: 部分未安裝"
    ALL_OK=false
fi

echo ""

if [ "$ALL_OK" = true ]; then
    echo "🎉 所有程式安裝完成！"
    echo ""
    echo "您現在可以雙擊 start.command 來啟動程式"
else
    echo "⚠️  部分程式安裝失敗，請查看上方錯誤訊息"
fi

echo ""
read -p "按 Enter 結束..."
