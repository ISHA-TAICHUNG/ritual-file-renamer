"""
壓縮模組 - 影片和圖片壓縮
保持解析度，降低檔案大小

使用：
- Pillow: JPEG 品質壓縮
- ffmpeg: H.264 影片壓縮
"""

from __future__ import annotations

import subprocess
import shutil
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

# 設定 logger
logger = logging.getLogger(__name__)

# 壓縮品質預設
COMPRESSION_PRESETS: dict[str, dict] = {
    "高品質（檔案較大）": {"image_quality": 85, "video_crf": 23},
    "平衡（推薦）": {"image_quality": 75, "video_crf": 28},
    "小檔案（品質略降）": {"image_quality": 60, "video_crf": 32},
}


def compress_image(
    input_path: Path,
    output_path: Path,
    quality: int = 75
) -> bool:
    """
    壓縮圖片為 JPEG 格式
    
    Args:
        input_path: 輸入圖片路徑
        output_path: 輸出圖片路徑
        quality: JPEG 品質 1-100（建議 60-85）
        
    Returns:
        是否成功
    """
    try:
        from PIL import Image
        
        with Image.open(input_path) as img:
            # 保留 EXIF
            exif = img.info.get('exif', b'')
            
            # 轉換為 RGB（處理 HEIC、RGBA 等格式）
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # 儲存為 JPEG
            output_jpg = output_path.with_suffix('.jpg')
            save_kwargs = {'quality': quality, 'optimize': True}
            if exif:
                save_kwargs['exif'] = exif
            
            img.save(output_jpg, 'JPEG', **save_kwargs)
        
        return True
        
    except ImportError:
        logger.error("Pillow 未安裝，無法壓縮圖片")
        shutil.copy2(input_path, output_path)
        return False
    except Exception as e:
        logger.warning(f"圖片壓縮失敗 ({input_path.name}): {e}")
        shutil.copy2(input_path, output_path)
        return False


def compress_video(
    input_path: Path,
    output_path: Path,
    crf: int = 28,
    preset: str = "medium"
) -> bool:
    """
    壓縮影片為 MP4 格式（H.264 編碼）
    
    Args:
        input_path: 輸入影片路徑
        output_path: 輸出影片路徑
        crf: 品質參數 0-51，越低品質越好
             - 18-22: 幾乎無損
             - 23-28: 高品質
             - 29-32: 中等品質
        preset: 編碼速度 (ultrafast/fast/medium/slow)
        
    Returns:
        是否成功
    """
    output_mp4 = output_path.with_suffix('.mp4')
    
    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-preset', preset,
        '-c:a', 'aac', '-b:a', '128k',
        '-movflags', '+faststart',
        str(output_mp4)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0
        
    except FileNotFoundError:
        logger.error("ffmpeg 未安裝，無法壓縮影片")
        return False
    except subprocess.TimeoutExpired:
        logger.warning(f"影片壓縮超時 ({input_path.name})")
        return False
    except Exception as e:
        logger.warning(f"影片壓縮失敗 ({input_path.name}): {e}")
        return False


def get_file_size_mb(path: Path) -> float:
    """取得檔案大小（MB）"""
    try:
        return path.stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        print(f"原始大小: {get_file_size_mb(path):.2f} MB")
