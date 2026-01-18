"""
Metadata 模組 - 提取圖片/影片的原始拍攝時間

支援：
- EXIF DateTimeOriginal (圖片)
- ffprobe creation_time (影片)
- 檔案系統時間 (fallback)
"""

from __future__ import annotations

import subprocess
import json
import logging
from functools import lru_cache
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional

# 設定 logger
logger = logging.getLogger(__name__)

# EXIF 日期標籤優先順序
EXIF_DATE_TAGS = (
    'EXIF DateTimeOriginal',
    'EXIF DateTimeDigitized',
    'Image DateTime'
)

# 影片 creation_time 可能的 key
VIDEO_TIME_KEYS = ('creation_time', 'com.apple.quicktime.creationdate')

# ISO 時間格式
ISO_DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


@lru_cache(maxsize=128)
def get_exif_datetime(image_path: Path) -> Optional[datetime]:
    """
    從圖片 EXIF 中提取原始拍攝時間
    
    使用 lru_cache 避免重複讀取同一檔案
    
    優先順序：
    1. EXIF DateTimeOriginal (原始拍攝時間)
    2. EXIF DateTimeDigitized (數位化時間)
    3. EXIF DateTime (修改時間)
    """
    try:
        import exifread
        
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False, stop_tag='EXIF DateTimeOriginal')
        
        for tag in EXIF_DATE_TAGS:
            if tag in tags:
                date_str = str(tags[tag])
                try:
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
        
        return None
        
    except ImportError:
        logger.warning("exifread 未安裝，無法讀取 EXIF")
        return None
    except Exception as e:
        logger.debug(f"EXIF 讀取失敗 ({image_path.name}): {e}")
        return None


@lru_cache(maxsize=128)
def get_video_creation_time(video_path: Path) -> Optional[datetime]:
    """
    使用 ffprobe 提取影片的原始建立時間
    
    使用 lru_cache 避免重複讀取同一檔案
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(video_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        tags = data.get('format', {}).get('tags', {})
        
        for key in VIDEO_TIME_KEYS:
            if key not in tags:
                continue
                
            time_str = tags[key]
            # 清理時區和微秒
            clean_str = time_str.split('.')[0].split('+')[0].replace('Z', '')
            
            for fmt in ISO_DATETIME_FORMATS:
                try:
                    return datetime.strptime(clean_str, fmt)
                except ValueError:
                    continue
        
        return None
        
    except FileNotFoundError:
        logger.warning("ffprobe 未安裝，無法讀取影片 metadata")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe 超時 ({video_path.name})")
        return None
    except Exception as e:
        logger.debug(f"影片 metadata 讀取失敗 ({video_path.name}): {e}")
        return None


def get_filesystem_time(file_path: Path) -> datetime:
    """
    取得檔案系統的建立時間 (fallback)
    
    macOS 使用 st_birthtime，其他系統使用 mtime
    """
    stat = file_path.stat()
    timestamp = getattr(stat, 'st_birthtime', stat.st_mtime)
    return datetime.fromtimestamp(timestamp)


def get_media_datetime(file_path: Path, is_video: bool = False) -> tuple[datetime, str]:
    """
    智慧取得媒體檔案的原始時間
    
    Args:
        file_path: 檔案路徑
        is_video: 是否為影片
        
    Returns:
        (datetime, source) - 時間和來源標記
        source: 'exif', 'video_meta', 'filesystem'
    """
    if is_video:
        video_time = get_video_creation_time(file_path)
        if video_time:
            return video_time, 'video_meta'
    else:
        exif_time = get_exif_datetime(file_path)
        if exif_time:
            return exif_time, 'exif'
    
    return get_filesystem_time(file_path), 'filesystem'


def clear_cache() -> None:
    """清除快取（用於重新處理相同檔案）"""
    get_exif_datetime.cache_clear()
    get_video_creation_time.cache_clear()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        is_video = path.suffix.lower() in {'.mp4', '.mov', '.m4v', '.avi'}
        
        dt, source = get_media_datetime(path, is_video)
        print(f"檔案: {path.name}")
        print(f"時間: {dt}")
        print(f"來源: {source}")
    else:
        print("用法: python metadata.py <檔案路徑>")
