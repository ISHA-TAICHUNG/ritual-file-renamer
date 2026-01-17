# 法事檔案自動配對命名工具

將法事錄影與照片自動配對並重新命名，方便整理和回傳。

## ✨ 功能特色

- **智慧圖像比對**：自動比對照片和影片內容進行配對
- **1:N 配對**：支援一張照片對應多個影片（001.jpg + 001a.mp4, 001b.mp4）
- **多種命名格式**：序號、姓名_序號、日期_序號 等
- **壓縮輸出**：可選壓縮，減少檔案大小
- **一鍵啟動**：雙擊即可使用

## 🚀 快速開始

### macOS 使用者

1. **安裝系統依賴**（首次使用）
   ```bash
   # 安裝 Homebrew（如果沒有）
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # 安裝必要工具
   brew install python tesseract tesseract-lang ffmpeg
   ```

2. **啟動程式**
   ```
   雙擊 start.command
   ```
   > 首次執行可能需要右鍵 → 打開（macOS 安全性）

## 📖 使用教學

1. **選擇輸入資料夾**：包含照片和影片的資料夾
2. **選擇輸出資料夾**：處理後檔案的存放位置
3. **設定選項**：
   - **配對模式**：圖像比對（推薦）/ 順序配對 / 時間配對
   - **命名格式**：序號（預設）/ 其他格式
   - **壓縮**：可選開啟
4. **點擊預覽**：確認配對結果
5. **點擊執行**：開始處理

## 📁 輸出範例

```
output/
├── 001.jpg       # 第一位
├── 001a.mp4      # 第一位的第一段影片
├── 001b.mp4      # 第一位的第二段影片
├── 002.jpg       # 第二位
├── 002.mp4       # 第二位的影片
└── ...
```

## ⚙️ 配對模式說明

| 模式 | 說明 | 適用情況 |
|------|------|---------|
| 圖像比對 | 自動比對照片與影片內容 | 一般情況（推薦） |
| 順序配對 | 依檔名順序配對 | 檔名有規律時 |
| 時間配對 | 依拍攝時間配對 | 原始 iPhone 檔案 |

## 🔧 系統需求

- macOS 10.15+
- Python 3.10+
- Tesseract OCR
- FFmpeg

## 📦 手動安裝

```bash
# 複製專案
git clone https://github.com/ISHA-TAICHUNG/ritual-file-renamer.git
cd ritual-file-renamer

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 執行
python3 gui.py
```

## 📝 更新日誌

### v2.0 (2026-01-17)
- 新增 GUI 圖形介面
- 新增圖像比對配對功能
- 新增 1:N 配對（一張照片配多個影片）
- 新增壓縮輸出功能
- 新增一鍵啟動腳本

### v1.0
- 基本配對和重命名功能
- CLI 命令列介面

## 📄 License

MIT License
