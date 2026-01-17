"""
OCR 模組 - 提取照片上的英文姓名
"""

import pytesseract
from PIL import Image
import re
from pathlib import Path


def extract_name_from_image(image_path: str | Path) -> str | None:
    """
    從照片中提取英文姓名
    
    照片格式：
    - 左下角有黑底白字標籤
    - 第一行：英文姓名（全大寫）
    - 第二行：日期
    
    Args:
        image_path: 照片路徑
        
    Returns:
        提取的英文姓名，如果失敗則返回 None
    """
    try:
        # 讀取圖片
        img = Image.open(image_path)
        
        # 取得圖片尺寸
        width, height = img.size
        
        # 裁切左下角區域（文字標籤通常在這裡）
        # 預設裁切左下角 1/3 寬度、1/4 高度的區域
        left = 0
        top = int(height * 0.75)
        right = int(width * 0.5)
        bottom = height
        
        cropped = img.crop((left, top, right, bottom))
        
        # OCR 辨識
        # 使用英文語言包，假設姓名是英文
        text = pytesseract.image_to_string(
            cropped,
            lang='eng',
            config='--psm 6'  # 假設是一個統一的文字區塊
        )
        
        # 解析文字，提取第一行（英文姓名）
        lines = text.strip().split('\n')
        if lines:
            # 第一行應該是英文姓名
            name_line = lines[0].strip()
            
            # 驗證是否為有效的英文姓名（只包含字母和空格）
            if re.match(r'^[A-Za-z\s]+$', name_line):
                # 轉換為標準格式：用底線連接，全大寫
                name = name_line.upper().replace(' ', '_')
                return name
        
        return None
        
    except Exception as e:
        print(f"OCR 錯誤 ({image_path}): {e}")
        return None


def extract_name_fullpage(image_path: str | Path) -> str | None:
    """
    從整張照片中提取英文姓名（備用方案）
    
    當裁切區域無法辨識時使用
    """
    try:
        img = Image.open(image_path)
        
        # 對整張圖片做 OCR
        text = pytesseract.image_to_string(img, lang='eng')
        
        # 尋找符合英文姓名格式的行
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            # 檢查是否為全大寫英文（可能是姓名）
            if re.match(r'^[A-Z][A-Z\s]+$', line) and len(line) > 3:
                name = line.replace(' ', '_')
                return name
        
        return None
        
    except Exception as e:
        print(f"OCR 錯誤 ({image_path}): {e}")
        return None


if __name__ == "__main__":
    # 測試用
    import sys
    if len(sys.argv) > 1:
        result = extract_name_from_image(sys.argv[1])
        if result:
            print(f"提取的姓名: {result}")
        else:
            print("無法提取姓名，嘗試全頁辨識...")
            result = extract_name_fullpage(sys.argv[1])
            if result:
                print(f"提取的姓名: {result}")
            else:
                print("辨識失敗")
