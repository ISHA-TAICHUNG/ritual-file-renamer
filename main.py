"""
Ritual File Renamer - 主程式
法事檔案自動配對命名工具
"""

import argparse
import shutil
from pathlib import Path
from tqdm import tqdm

from src.ocr import extract_name_from_image, extract_name_fullpage
from src.pairing import scan_media_files, pair_files, FilePair


def rename_and_copy(
    pairs: list[FilePair],
    output_dir: str | Path,
    dry_run: bool = False
) -> dict:
    """
    重命名配對的檔案並複製到輸出資料夾
    
    Args:
        pairs: 配對列表
        output_dir: 輸出資料夾
        dry_run: 如果為 True，只預覽不實際執行
        
    Returns:
        處理結果統計
    """
    output_path = Path(output_dir)
    
    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)
    
    stats = {
        'success': 0,
        'ocr_failed': 0,
        'errors': []
    }
    
    for pair in tqdm(pairs, desc="處理中"):
        try:
            # OCR 提取姓名
            name = extract_name_from_image(pair.photo.path)
            
            if not name:
                # 嘗試全頁辨識
                name = extract_name_fullpage(pair.photo.path)
            
            if not name:
                # OCR 失敗，使用序號
                name = f"UNKNOWN_{pair.sequence:03d}"
                stats['ocr_failed'] += 1
                print(f"\n警告: 無法辨識 {pair.photo.path.name}，使用序號命名")
            
            # 生成新檔名
            seq = f"{pair.sequence:03d}"
            photo_ext = pair.photo.path.suffix.lower()
            video_ext = pair.video.path.suffix.lower()
            
            # 統一影片格式為 .mp4（如果是 .mov 保持原樣）
            new_photo_name = f"{name}_{seq}{photo_ext}"
            new_video_name = f"{name}_{seq}{video_ext}"
            
            new_photo_path = output_path / new_photo_name
            new_video_path = output_path / new_video_name
            
            if dry_run:
                print(f"\n[預覽] {pair.photo.path.name} → {new_photo_name}")
                print(f"[預覽] {pair.video.path.name} → {new_video_name}")
            else:
                # 複製檔案（保留原檔）
                shutil.copy2(pair.photo.path, new_photo_path)
                shutil.copy2(pair.video.path, new_video_path)
            
            stats['success'] += 1
            
        except Exception as e:
            stats['errors'].append({
                'photo': pair.photo.path.name,
                'video': pair.video.path.name,
                'error': str(e)
            })
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='法事檔案自動配對命名工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  python main.py ./input ./output
  python main.py ./input ./output --dry-run
        '''
    )
    
    parser.add_argument('input_dir', help='輸入資料夾（包含照片和影片）')
    parser.add_argument('output_dir', help='輸出資料夾')
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='預覽模式，不實際執行'
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("法事檔案自動配對命名工具")
    print("=" * 50)
    print()
    
    # 掃描檔案
    print(f"掃描資料夾: {args.input_dir}")
    files = scan_media_files(args.input_dir)
    print(f"找到 {len(files)} 個媒體檔案")
    
    # 配對
    print("\n開始配對...")
    pairs = pair_files(files)
    print(f"成功配對 {len(pairs)} 組")
    
    if not pairs:
        print("沒有找到可配對的檔案，程式結束")
        return
    
    # 重命名和複製
    print(f"\n輸出到: {args.output_dir}")
    if args.dry_run:
        print("【預覽模式】")
    
    stats = rename_and_copy(pairs, args.output_dir, dry_run=args.dry_run)
    
    # 報告
    print("\n" + "=" * 50)
    print("處理結果")
    print("=" * 50)
    print(f"成功: {stats['success']} 組")
    print(f"OCR 失敗（使用序號）: {stats['ocr_failed']} 組")
    
    if stats['errors']:
        print(f"錯誤: {len(stats['errors'])} 組")
        for err in stats['errors']:
            print(f"  - {err['photo']}: {err['error']}")


if __name__ == "__main__":
    main()
