"""
影像比對模組 - 用圖像相似度配對照片和影片
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_video_frame(video_path: Path, frame_position: float = 0.5) -> Optional[np.ndarray]:
    """
    從影片擷取指定位置的幀
    
    Args:
        video_path: 影片路徑
        frame_position: 擷取位置（0.0~1.0），預設 0.5 = 影片中間
        
    Returns:
        OpenCV 圖像 (numpy array)，失敗返回 None
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None
        
        # 取得總幀數，擷取指定位置
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_number = int(total_frames * frame_position)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return frame
        return None
        
    except Exception as e:
        logger.warning(f"擷取影片幀失敗 ({video_path}): {e}")
        return None


def load_image(image_path: Path) -> Optional[np.ndarray]:
    """載入圖片"""
    try:
        img = cv2.imread(str(image_path))
        return img
    except Exception as e:
        logger.warning(f"載入圖片失敗 ({image_path}): {e}")
        return None


def compute_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    計算兩張圖片的相似度
    
    使用 ORB 特徵點匹配，返回 0-1 的相似度分數
    """
    try:
        # 轉灰階
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # 調整大小以加速比對
        target_size = (400, 300)
        gray1 = cv2.resize(gray1, target_size)
        gray2 = cv2.resize(gray2, target_size)
        
        # 使用 ORB 特徵點
        orb = cv2.ORB_create(nfeatures=500)
        kp1, des1 = orb.detectAndCompute(gray1, None)
        kp2, des2 = orb.detectAndCompute(gray2, None)
        
        if des1 is None or des2 is None:
            # 無法偵測特徵點，使用直方圖比對
            return histogram_similarity(gray1, gray2)
        
        # BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        
        # 計算相似度（匹配數 / 總特徵點數）
        if len(kp1) == 0 or len(kp2) == 0:
            return 0.0
        
        # 過濾好的匹配
        good_matches = [m for m in matches if m.distance < 50]
        
        similarity = len(good_matches) / min(len(kp1), len(kp2))
        return min(similarity, 1.0)
        
    except Exception as e:
        logger.warning(f"計算相似度失敗: {e}")
        return 0.0


def histogram_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """使用直方圖比對計算相似度（備用方案）"""
    try:
        hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
        
        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)
        
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return max(0, similarity)  # 相關係數可能為負
        
    except Exception:
        return 0.0


def find_best_video_match(photo_path: Path, video_paths: list[Path]) -> tuple[Optional[Path], float]:
    """
    為一張照片找到最佳匹配的影片
    
    Args:
        photo_path: 照片路徑
        video_paths: 候選影片路徑列表
        
    Returns:
        (最佳匹配的影片路徑, 相似度分數)
    """
    photo_img = load_image(photo_path)
    if photo_img is None:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    for video_path in video_paths:
        frame = extract_video_frame(video_path)
        if frame is None:
            continue
        
        score = compute_similarity(photo_img, frame)
        
        if score > best_score:
            best_score = score
            best_match = video_path
    
    return best_match, best_score


def match_photos_to_videos(
    photo_paths: list[Path],
    video_paths: list[Path],
    threshold: float = 0.1,
    multi_video: bool = True
) -> list[tuple[Path, list[tuple[Path, float]]]]:
    """
    用圖像相似度配對所有照片和影片
    
    支援 1:N 配對（一張照片配多個影片）
    
    Args:
        photo_paths: 照片路徑列表
        video_paths: 影片路徑列表
        threshold: 最低相似度門檻
        multi_video: 是否允許一張照片配多個影片
        
    Returns:
        [(照片路徑, [(影片路徑, 相似度), ...]), ...]
    """
    # 預先擷取所有影片幀（避免重複擷取）
    video_frames = {}
    for video_path in video_paths:
        frame = extract_video_frame(video_path)
        if frame is not None:
            video_frames[video_path] = frame
    
    # 計算每張照片對所有影片的相似度
    photo_video_scores = {}
    
    for photo_path in photo_paths:
        photo_img = load_image(photo_path)
        if photo_img is None:
            continue
        
        scores = []
        for video_path, frame in video_frames.items():
            score = compute_similarity(photo_img, frame)
            if score >= threshold:
                scores.append((video_path, score))
        
        # 按相似度排序
        scores.sort(key=lambda x: x[1], reverse=True)
        photo_video_scores[photo_path] = scores
    
    # 分配影片給照片
    results = []
    used_videos = set()
    
    if multi_video:
        # 1:N 模式：每個影片分配給相似度最高的照片
        video_to_photo = {}  # video -> (photo, score)
        
        for photo_path, scores in photo_video_scores.items():
            for video_path, score in scores:
                if video_path not in video_to_photo:
                    video_to_photo[video_path] = (photo_path, score)
                elif score > video_to_photo[video_path][1]:
                    video_to_photo[video_path] = (photo_path, score)
        
        # 反轉：按照片分組影片
        photo_to_videos = {}
        for video_path, (photo_path, score) in video_to_photo.items():
            if photo_path not in photo_to_videos:
                photo_to_videos[photo_path] = []
            photo_to_videos[photo_path].append((video_path, score))
        
        # 按照片順序輸出
        for photo_path in photo_paths:
            if photo_path in photo_to_videos:
                videos = photo_to_videos[photo_path]
                # 按影片檔名排序
                videos.sort(key=lambda x: x[0].name)
                results.append((photo_path, videos))
    else:
        # 1:1 模式
        for photo_path in photo_paths:
            if photo_path not in photo_video_scores:
                continue
            
            for video_path, score in photo_video_scores[photo_path]:
                if video_path not in used_videos:
                    results.append((photo_path, [(video_path, score)]))
                    used_videos.add(video_path)
                    break
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        photo = Path(sys.argv[1])
        video = Path(sys.argv[2])
        
        photo_img = load_image(photo)
        frame = extract_video_frame(video)
        
        if photo_img is not None and frame is not None:
            score = compute_similarity(photo_img, frame)
            print(f"相似度: {score:.2f}")
        else:
            print("載入失敗")
    else:
        print("用法: python matching.py <照片> <影片>")
