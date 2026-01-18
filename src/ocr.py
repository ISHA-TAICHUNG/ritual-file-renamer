"""
OCR 模組 - 提取照片上的英文姓名

使用 Tesseract OCR + OpenCV 預處理
"""

import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
from pathlib import Path


def preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    預處理圖片以提升 OCR 效果
    """
    # 轉灰階
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # 放大（小文字需要放大）
    scale = 2
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # 二值化（黑白）
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 降噪
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
    
    return denoised


def extract_name_from_image(image_path: str | Path) -> str | None:
    """
    從照片中提取英文姓名
    
    會嘗試多個區域：右下角（相框）、下半部
    """
    try:
        # 使用 OpenCV 讀取
        img = cv2.imread(str(image_path))
        if img is None:
            return None
            
        height, width = img.shape[:2]
        
        # 嘗試多個區域
        regions = [
            # 右下角（相框通常在這裡，較小區域更精確）
            (int(width * 0.5), int(height * 0.65), width, height),
            # 右下角更大區域
            (int(width * 0.35), int(height * 0.5), width, height),
            # 下半部中間
            (int(width * 0.2), int(height * 0.6), int(width * 0.8), height),
        ]
        
        for left, top, right, bottom in regions:
            cropped = img[top:bottom, left:right]
            
            # 預處理
            processed = preprocess_for_ocr(cropped)
            
            # OCR - 嘗試多種 PSM 模式
            for psm in [6, 11, 3]:  # 6=block, 11=sparse, 3=auto
                text = pytesseract.image_to_string(
                    processed,
                    lang='eng',
                    config=f'--psm {psm} --oem 3'
                )
                
                name = _extract_name_from_text(text)
                if name:
                    return name
        
        return None
        
    except Exception as e:
        print(f"OCR 錯誤 ({image_path}): {e}")
        return None


def _extract_name_from_text(text: str) -> str | None:
    """從 OCR 文字中提取姓名"""
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # 移除數字、日期、特殊字符
        cleaned = re.sub(r'[0-9/\-\.\(\)\[\]:]+', ' ', line)
        cleaned = cleaned.strip()
        
        if not cleaned or len(cleaned) < 3:
            continue
        
        # 檢查是否為有效的英文姓名
        # 支援: LIN,HSI-TSUNG / Chen peiru / CHANG CHIA HAO
        if re.match(r'^[A-Za-z][A-Za-z,\s\-\']+[A-Za-z]$', cleaned):
            # 標準化
            name = cleaned.upper()
            name = re.sub(r'[,\s\-\']+', '_', name)
            name = re.sub(r'_+', '_', name)
            name = name.strip('_')
            
            # 過濾掉太短或只有一個詞的結果
            if len(name) >= 4 and '_' in name:
                return name
            elif len(name) >= 6:  # 單詞但夠長
                return name
    
    return None


def extract_name_fullpage(image_path: str | Path) -> str | None:
    """從整張照片中提取英文姓名（備用方案）"""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return None
        
        # 預處理
        processed = preprocess_for_ocr(img)
        
        # OCR
        text = pytesseract.image_to_string(processed, lang='eng', config='--psm 3')
        
        return _extract_name_from_text(text)
        
    except Exception as e:
        print(f"OCR 錯誤 ({image_path}): {e}")
        return None


if __name__ == "__main__":
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
