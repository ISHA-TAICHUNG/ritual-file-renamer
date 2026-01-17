# Ritual File Renamer 法事檔案自動配對命名工具

自動化處理法事錄影與個人照片的配對與重命名工具。

## 問題背景

每天處理 100+ 筆法事錄影，需要將：
- 個人照片（含英文姓名）
- 對應的法事錄影

配對並重新命名成相同檔名，方便回傳給客戶。

## 設計流程

### 作業流程

```
1. 放照片到法壇前
2. 用 iPhone 拍那張照片（照片檔）
3. 開始錄影（影片檔）
4. 重複 1~3

↓ 一天結束 ↓

5. 傳到電腦固定資料夾
6. 執行程式
   ├── 時間排序 → 照片和影片配對
   ├── OCR 照片 → 提取英文姓名
   └── 重命名：姓名_序號.jpg / 姓名_序號.mp4
7. 輸出到雲端資料夾
```

### 照片格式

- 左下角有黑底白字標籤
- 第一行：英文姓名（全大寫）
- 第二行：日期（佛曆或西元）

範例：
```
CHANG CHIA HAO
2535/05/16
```

### 技術架構

```
Python
├── pytesseract (OCR)
├── OpenCV (影像處理)
├── ffmpeg (影片幀擷取)
└── Pillow (圖片處理)
```

### 配對邏輯

| 優先級 | 方法 | 說明 |
|--------|------|------|
| 1 | 時間順序 | 照片和影片交錯，依時間戳配對 |
| 2 | 影像相似度 | 備用方案，處理例外情況 |

### 檔案結構

```
輸入資料夾/
├── IMG_0001.jpg  (拍照：照片01)
├── IMG_0002.MOV  (錄影：法事01)
├── IMG_0003.jpg  (拍照：照片02)
├── IMG_0004.MOV  (錄影：法事02)
└── ...

輸出資料夾/
├── CHANG_CHIA_HAO_001.jpg
├── CHANG_CHIA_HAO_001.mp4
├── WANG_XIAO_MING_002.jpg
├── WANG_XIAO_MING_002.mp4
└── ...
```

## 待實作

- [ ] 基本框架
- [ ] OCR 功能（提取英文姓名）
- [ ] 時間戳排序配對
- [ ] 檔案重命名
- [ ] 輸出到指定資料夾
- [ ] 錯誤處理與日誌
- [ ] GUI 介面（可選）

## 環境需求

- **作業系統**：macOS
- **Python**：3.10+
- **Tesseract OCR**
- **ffmpeg**

### 安裝指令（macOS）

```bash
# 安裝 Homebrew（如果還沒裝）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝依賴
brew install tesseract tesseract-lang ffmpeg python@3.11

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝 Python 套件（待實作）
pip install -r requirements.txt
```

## 使用方式

待實作...

## 注意事項

1. 作業時不能中途拍其他東西（會打亂順序）
2. 重錄時要刪掉失敗的影片
3. 使用同一支 iPhone 作業
