"""
影片分割模組 - 使用 ffmpeg 將影片平均分割成多段
"""

from __future__ import annotations

import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_video_duration(video_path: Path) -> Optional[float]:
    """
    取得影片總長度（秒）
    
    Args:
        video_path: 影片檔案路徑
        
    Returns:
        影片長度（秒），失敗時返回 None
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        logger.warning(f"無法取得影片長度 ({video_path.name}): {e}")
    
    return None


def split_video(
    input_path: Path,
    output_dir: Path,
    num_segments: int,
    base_name: str,
    ext: str = ".mp4",
    compress: bool = False,
    crf: int = 28
) -> list[Path]:
    """
    將影片平均分割成指定段數
    
    Args:
        input_path: 輸入影片路徑
        output_dir: 輸出目錄
        num_segments: 分割段數 (2-10)
        base_name: 輸出檔案基礎名稱（不含副檔名）
        ext: 輸出副檔名
        compress: 是否壓縮
        crf: 壓縮品質參數
        
    Returns:
        分割後的檔案路徑列表
    """
    if num_segments < 2 or num_segments > 10:
        raise ValueError(f"分割段數必須介於 2-10：{num_segments}")
    
    # 取得影片總長度
    duration = get_video_duration(input_path)
    if duration is None:
        logger.error(f"無法取得影片長度，跳過分割：{input_path}")
        return []
    
    # 計算每段長度
    segment_duration = duration / num_segments
    
    # 子序號標籤：a, b, c, d, e, f, g, h, i, j
    sub_labels = 'abcdefghij'
    
    output_files = []
    
    for i in range(num_segments):
        start_time = i * segment_duration
        sub_label = sub_labels[i]
        output_name = f"{base_name}{sub_label}{ext}"
        output_path = output_dir / output_name
        
        # 建立 ffmpeg 命令
        if compress:
            # 壓縮模式：重新編碼
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', str(input_path),
                '-t', str(segment_duration),
                '-c:v', 'libx264',
                '-crf', str(crf),
                '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                str(output_path)
            ]
        else:
            # 不壓縮：使用 copy 模式（快速但可能不精確）
            # 為了精確分割，還是使用重新編碼但保持高品質
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', str(input_path),
                '-t', str(segment_duration),
                '-c:v', 'libx264',
                '-crf', '18',  # 高品質
                '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart',
                str(output_path)
            ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 分鐘超時
            )
            
            if result.returncode == 0 and output_path.exists():
                output_files.append(output_path)
                logger.info(f"分割完成：{output_name}")
            else:
                logger.warning(f"分割失敗 ({output_name}): {result.stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            logger.warning(f"分割超時：{output_name}")
        except FileNotFoundError:
            logger.error("ffmpeg 未安裝")
            break
        except Exception as e:
            logger.warning(f"分割錯誤 ({output_name}): {e}")
    
    return output_files


def get_segment_count_from_option(option: str) -> int:
    """
    從下拉選單選項解析分割段數
    
    Args:
        option: 選單選項，如 "不分割"、"2 段"、"3 段" 等
        
    Returns:
        分割段數，「不分割」返回 1
    """
    if option == "不分割":
        return 1
    
    try:
        # 解析 "2 段" -> 2
        return int(option.replace(" 段", ""))
    except ValueError:
        return 1


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) >= 3:
        input_file = Path(sys.argv[1])
        num_segs = int(sys.argv[2])
        output_dir = input_file.parent / "split_output"
        output_dir.mkdir(exist_ok=True)
        
        print(f"分割 {input_file} 為 {num_segs} 段...")
        results = split_video(input_file, output_dir, num_segs, "test")
        print(f"完成：{len(results)} 個檔案")
        for f in results:
            print(f"  - {f.name}")
