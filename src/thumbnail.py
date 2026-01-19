"""
縮圖生成模組 - 產生照片和影片的縮圖供 GUI 預覽
"""

from pathlib import Path
from typing import Optional
import cv2
from PIL import Image
import io

# 縮圖尺寸
THUMBNAIL_SIZE = (80, 100)  # 寬 x 高


def generate_image_thumbnail(image_path: Path, size: tuple = THUMBNAIL_SIZE) -> Optional[bytes]:
    """
    產生照片縮圖
    
    Args:
        image_path: 照片路徑
        size: 縮圖尺寸 (寬, 高)
        
    Returns:
        PNG 格式的縮圖 bytes，失敗返回 None
    """
    try:
        with Image.open(image_path) as img:
            # 轉換為 RGB（處理 HEIC 等格式）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 計算等比例縮放
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 輸出為 PNG bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
            
    except Exception as e:
        print(f"生成照片縮圖失敗 ({image_path.name}): {e}")
        return None


def generate_video_thumbnail(video_path: Path, size: tuple = THUMBNAIL_SIZE, frame_position: float = 0.5) -> Optional[bytes]:
    """
    產生影片縮圖（擷取指定位置的幀）
    
    Args:
        video_path: 影片路徑
        size: 縮圖尺寸 (寬, 高)
        frame_position: 擷取位置（0.0~1.0，預設 0.5 = 中間）
        
    Returns:
        PNG 格式的縮圖 bytes，失敗返回 None
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None
        
        # 取得影片總幀數，擷取指定位置
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_number = int(total_frames * frame_position)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            return None
        
        # BGR 轉 RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 轉成 PIL Image 並縮放
        img = Image.fromarray(frame_rgb)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # 輸出為 PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
        
    except Exception as e:
        print(f"生成影片縮圖失敗 ({video_path.name}): {e}")
        return None


def generate_thumbnail(file_path: Path, is_video: bool, size: tuple = THUMBNAIL_SIZE) -> Optional[bytes]:
    """
    自動判斷類型並產生縮圖
    """
    if is_video:
        return generate_video_thumbnail(file_path, size)
    else:
        return generate_image_thumbnail(file_path, size)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        is_video = path.suffix.lower() in {'.mp4', '.mov', '.m4v', '.avi'}
        
        thumb = generate_thumbnail(path, is_video)
        if thumb:
            output = path.with_suffix('.thumb.png')
            with open(output, 'wb') as f:
                f.write(thumb)
            print(f"縮圖已儲存: {output}")
        else:
            print("生成縮圖失敗")
