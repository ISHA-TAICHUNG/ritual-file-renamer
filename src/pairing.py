"""
檔案配對模組 - 依時間戳配對照片和影片

支援從 EXIF / 影片 metadata 讀取原始拍攝時間，
適用於透過 LINE 等通訊軟體下載的檔案。
"""

from pathlib import Path
from datetime import datetime
import os
from dataclasses import dataclass, field

from .metadata import get_media_datetime


# 支援的檔案格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.avi'}


@dataclass
class MediaFile:
    """媒體檔案資訊"""
    path: Path
    is_video: bool
    created_time: datetime
    time_source: str = 'filesystem'  # 'exif', 'video_meta', 'filesystem'
    
    @property
    def extension(self) -> str:
        return self.path.suffix.lower()


@dataclass
class FilePair:
    """配對的照片和影片"""
    photo: MediaFile
    video: MediaFile
    sequence: int  # 序號


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
        
        # 使用智慧時間提取（優先 EXIF/影片 metadata）
        created_time, time_source = get_media_datetime(file_path, is_video)
        
        media_file = MediaFile(
            path=file_path,
            is_video=is_video,
            created_time=created_time,
            time_source=time_source
        )
        media_files.append(media_file)
    
    # 依建立時間排序
    media_files.sort(key=lambda x: x.created_time)
    
    return media_files


def pair_files(media_files: list[MediaFile], mode: str = 'time') -> list[FilePair]:
    """
    配對照片和影片
    
    假設工作流程是：拍照 → 錄影 → 拍照 → 錄影 ...
    依照時間順序，相鄰的照片和影片應該是一對
    
    Args:
        media_files: 依時間排序的媒體檔案列表
        mode: 配對模式
            - 'time': 時間配對（照片時間 < 影片時間）
            - 'order': 順序配對（第1張照片配第1個影片，依此類推）
        
    Returns:
        配對結果列表
    """
    pairs = []
    photos = [f for f in media_files if not f.is_video]
    videos = [f for f in media_files if f.is_video]
    
    if len(photos) != len(videos):
        print(f"警告: 照片數量 ({len(photos)}) 和影片數量 ({len(videos)}) 不一致")
    
    if mode == 'image':
        # 圖像比對配對：擷取影片第一幀，和照片做相似度比對
        from .matching import match_photos_to_videos
        
        photo_paths = [f.path for f in photos]
        video_paths = [f.path for f in videos]
        
        matches = match_photos_to_videos(photo_paths, video_paths)
        
        # 建立 path -> MediaFile 的映射
        photo_map = {f.path: f for f in photos}
        video_map = {f.path: f for f in videos}
        
        for i, (photo_path, video_path, score) in enumerate(matches, 1):
            pair = FilePair(
                photo=photo_map[photo_path],
                video=video_map[video_path],
                sequence=i
            )
            pairs.append(pair)
            print(f"  配對 {i}: {photo_path.name} + {video_path.name} (相似度: {score:.2f})")
    
    elif mode == 'order':
        # 順序配對：依檔名排序後配對
        photos_sorted = sorted(photos, key=lambda x: x.path.name)
        videos_sorted = sorted(videos, key=lambda x: x.path.name)
        
        for i, (photo, video) in enumerate(zip(photos_sorted, videos_sorted), 1):
            pair = FilePair(photo=photo, video=video, sequence=i)
            pairs.append(pair)
        
        # 報告未配對的檔案
        if len(photos) > len(videos):
            for photo in photos[len(videos):]:
                print(f"警告: 照片 {photo.path.name} 沒有對應的影片")
        elif len(videos) > len(photos):
            for video in videos[len(photos):]:
                print(f"警告: 影片 {video.path.name} 沒有對應的照片")
    else:
        # 時間配對：依照時間順序，每張照片對應下一個影片
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
        print(f"  照片: {pair.photo.path.name}")
        print(f"        時間: {pair.photo.created_time} [{pair.photo.time_source}]")
        print(f"  影片: {pair.video.path.name}")
        print(f"        時間: {pair.video.created_time} [{pair.video.time_source}]")
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
