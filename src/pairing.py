"""
檔案配對模組 - 依時間戳配對照片和影片
"""

from pathlib import Path
from datetime import datetime
import os
from dataclasses import dataclass


# 支援的檔案格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.avi'}


@dataclass
class MediaFile:
    """媒體檔案資訊"""
    path: Path
    is_video: bool
    created_time: datetime
    
    @property
    def extension(self) -> str:
        return self.path.suffix.lower()


@dataclass
class FilePair:
    """配對的照片和影片"""
    photo: MediaFile
    video: MediaFile
    sequence: int  # 序號


def get_file_created_time(file_path: Path) -> datetime:
    """
    取得檔案建立時間
    
    優先使用檔案的 birthtime（建立時間），
    如果不可用則使用 mtime（修改時間）
    """
    stat = file_path.stat()
    
    # macOS 支援 st_birthtime
    if hasattr(stat, 'st_birthtime'):
        return datetime.fromtimestamp(stat.st_birthtime)
    
    # 其他系統使用 mtime
    return datetime.fromtimestamp(stat.st_mtime)


def scan_media_files(input_dir: str | Path) -> list[MediaFile]:
    """
    掃描資料夾中的所有媒體檔案
    
    Args:
        input_dir: 輸入資料夾路徑
        
    Returns:
        MediaFile 列表，依建立時間排序
    """
    input_path = Path(input_dir)
    media_files = []
    
    if not input_path.exists():
        raise FileNotFoundError(f"資料夾不存在: {input_dir}")
    
    for file_path in input_path.iterdir():
        if not file_path.is_file():
            continue
            
        ext = file_path.suffix.lower()
        
        if ext in IMAGE_EXTENSIONS:
            is_video = False
        elif ext in VIDEO_EXTENSIONS:
            is_video = True
        else:
            continue  # 跳過不支援的格式
        
        media_file = MediaFile(
            path=file_path,
            is_video=is_video,
            created_time=get_file_created_time(file_path)
        )
        media_files.append(media_file)
    
    # 依建立時間排序
    media_files.sort(key=lambda x: x.created_time)
    
    return media_files


def pair_files(media_files: list[MediaFile]) -> list[FilePair]:
    """
    配對照片和影片
    
    假設工作流程是：拍照 → 錄影 → 拍照 → 錄影 ...
    依照時間順序，相鄰的照片和影片應該是一對
    
    Args:
        media_files: 依時間排序的媒體檔案列表
        
    Returns:
        配對結果列表
    """
    pairs = []
    photos = [f for f in media_files if not f.is_video]
    videos = [f for f in media_files if f.is_video]
    
    if len(photos) != len(videos):
        print(f"警告: 照片數量 ({len(photos)}) 和影片數量 ({len(videos)}) 不一致")
    
    # 配對策略：依照時間順序，每張照片對應下一個影片
    sequence = 1
    photo_idx = 0
    video_idx = 0
    
    while photo_idx < len(photos) and video_idx < len(videos):
        photo = photos[photo_idx]
        video = videos[video_idx]
        
        # 照片應該在影片之前
        if photo.created_time <= video.created_time:
            pair = FilePair(
                photo=photo,
                video=video,
                sequence=sequence
            )
            pairs.append(pair)
            sequence += 1
            photo_idx += 1
            video_idx += 1
        else:
            # 時序不對，跳過這個影片
            print(f"警告: 影片 {video.path.name} 沒有對應的照片")
            video_idx += 1
    
    # 報告未配對的檔案
    while photo_idx < len(photos):
        print(f"警告: 照片 {photos[photo_idx].path.name} 沒有對應的影片")
        photo_idx += 1
    
    while video_idx < len(videos):
        print(f"警告: 影片 {videos[video_idx].path.name} 沒有對應的照片")
        video_idx += 1
    
    return pairs


def print_pairs(pairs: list[FilePair]) -> None:
    """印出配對結果"""
    print(f"\n找到 {len(pairs)} 對配對：\n")
    for pair in pairs:
        print(f"[{pair.sequence:03d}]")
        print(f"  照片: {pair.photo.path.name} ({pair.photo.created_time})")
        print(f"  影片: {pair.video.path.name} ({pair.video.created_time})")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
        files = scan_media_files(input_dir)
        print(f"掃描到 {len(files)} 個媒體檔案")
        
        pairs = pair_files(files)
        print_pairs(pairs)
    else:
        print("用法: python pairing.py <輸入資料夾>")
