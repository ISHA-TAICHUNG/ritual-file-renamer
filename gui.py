"""
Ritual File Renamer - GUI 應用程式
法事檔案自動配對命名工具（圖形介面版）
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from pathlib import Path
from datetime import datetime
import shutil
import subprocess

from src.ocr import extract_name_from_image, extract_name_fullpage
from src.pairing import scan_media_files, pair_files, pair_files_by_time, FilePair
from src.compress import compress_image, compress_video, get_file_size_mb, COMPRESSION_PRESETS
from src.video_split import split_video, get_segment_count_from_option

from src.thumbnail import generate_thumbnail
from PIL import Image
import io


# 設定外觀
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# 命名格式選項
NAMING_FORMATS = {
    "自訂內容_序號": "{prefix}_{seq}",
    "序號": "{seq}",
}


class RitualRenamerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("法事檔案自動配對命名工具")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # 狀態變數
        self.input_dir = ctk.StringVar()
        self.output_dir = ctk.StringVar()
        self.naming_format = ctk.StringVar(value="序號")
        self.custom_prefix = ctk.StringVar(value="")  # 自訂前綴
        self.compress_enabled = ctk.BooleanVar(value=False)
        self.compress_preset = ctk.StringVar(value="平衡（推薦）")
        self.video_split_count = ctk.StringVar(value="不分割")  # 影片分割段數
        self.pairing_mode = ctk.StringVar(value="順序配對")  # 配對模式
        self.time_tolerance = ctk.StringVar(value="60")  # 時間容錯（秒）

        self.pairs = []
        self.photos = []  # 照片列表（可手動調整順序）
        self.videos = []  # 影片列表（可手動調整順序）
        self.is_processing = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        # 主容器
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 標題列（包含標題和按鈕）
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))
        
        # 標題（左側）
        title_label = ctk.CTkLabel(
            title_frame,
            text="🕯️ 法事檔案自動配對命名工具",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left")
        
        # 按鈕區（右側）
        self.run_btn = ctk.CTkButton(
            title_frame,
            text="▶️ 執行",
            width=100,
            height=36,
            fg_color="green",
            hover_color="darkgreen",
            command=self._run
        )
        self.run_btn.pack(side="right", padx=5)
        
        self.preview_btn = ctk.CTkButton(
            title_frame,
            text="👁️ 預覽",
            width=100,
            height=36,
            command=self._preview
        )
        self.preview_btn.pack(side="right", padx=5)
        
        # 主內容區（左右分欄）
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        
        # 左側：設定和配對列表
        left_frame = ctk.CTkFrame(content_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # 右側：大型預覽區
        right_frame = ctk.CTkFrame(content_frame)
        right_frame.pack(side="right", fill="y", padx=(10, 0))
        
        ctk.CTkLabel(
            right_frame, 
            text="🔍 大圖預覽", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)
        
        self.large_preview_label = ctk.CTkLabel(
            right_frame,
            text="將滑鼠移到\n縮圖上\n查看大圖",
            width=400,
            height=300,
            fg_color=("gray85", "gray20")
        )
        self.large_preview_label.pack(padx=10, pady=5)
        
        self.preview_filename_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=13),
            wraplength=380
        )
        self.preview_filename_label.pack(pady=5)
        
        self.large_preview_image = None  # 保持引用避免 GC
        
        # 設定區（在左側）
        settings_frame = ctk.CTkFrame(left_frame)
        settings_frame.pack(fill="x", pady=10)
        
        # 輸入資料夾
        input_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(input_frame, text="輸入資料夾:", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(input_frame, textvariable=self.input_dir, width=450).pack(side="left", padx=5)
        ctk.CTkButton(input_frame, text="選擇", width=80, command=self._select_input).pack(side="left")
        
        # 輸出資料夾
        output_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        output_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(output_frame, text="輸出資料夾:", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(output_frame, textvariable=self.output_dir, width=450).pack(side="left", padx=5)
        ctk.CTkButton(output_frame, text="選擇", width=80, command=self._select_output).pack(side="left")
        
        # 命名格式選擇
        format_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        format_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(format_frame, text="命名格式:", width=100, anchor="w").pack(side="left")
        
        format_dropdown = ctk.CTkOptionMenu(
            format_frame,
            variable=self.naming_format,
            values=list(NAMING_FORMATS.keys()),
            width=150,
            command=self._on_format_change
        )
        format_dropdown.pack(side="left", padx=5)
        
        # 自訂前綴輸入框
        ctk.CTkLabel(format_frame, text="自訂內容:", width=80).pack(side="left", padx=(15, 0))
        self.prefix_entry = ctk.CTkEntry(
            format_frame,
            textvariable=self.custom_prefix,
            width=150,
            placeholder_text="輸入自訂內容"
        )
        self.prefix_entry.pack(side="left", padx=5)
        self.prefix_entry.configure(state="disabled")  # 預設禁用（選「序號」時）
        
        # 格式預覽
        self.format_preview = ctk.CTkLabel(
            format_frame,
            text="預覽: 001.jpg",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.format_preview.pack(side="left", padx=15)
        
        # 影片分割設定
        split_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        split_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(split_frame, text="影片分割:", width=100, anchor="w").pack(side="left")
        
        split_options = ["不分割"] + [f"{i} 段" for i in range(2, 11)]
        split_dropdown = ctk.CTkOptionMenu(
            split_frame,
            variable=self.video_split_count,
            values=split_options,
            width=150
        )
        split_dropdown.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            split_frame,
            text="將每個影片平均分割成多段",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(side="left", padx=10)
        
        # 配對模式選擇
        pairing_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        pairing_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(pairing_frame, text="配對模式:", width=100, anchor="w").pack(side="left")
        
        pairing_dropdown = ctk.CTkOptionMenu(
            pairing_frame,
            variable=self.pairing_mode,
            values=["順序配對", "時間比對", "圖像比對"],
            width=120,
            command=self._on_pairing_mode_change
        )
        pairing_dropdown.pack(side="left", padx=5)
        
        # 時間容錯設定（預設隱藏）
        self.tolerance_label = ctk.CTkLabel(pairing_frame, text="容錯:", width=50)
        self.tolerance_label.pack(side="left", padx=(15, 0))
        
        self.tolerance_entry = ctk.CTkEntry(
            pairing_frame,
            textvariable=self.time_tolerance,
            width=60
        )
        self.tolerance_entry.pack(side="left", padx=5)
        
        self.tolerance_unit = ctk.CTkLabel(
            pairing_frame,
            text="秒",
            font=ctk.CTkFont(size=12)
        )
        self.tolerance_unit.pack(side="left")
        
        self.pairing_tip = ctk.CTkLabel(
            pairing_frame,
            text="照片後 N 秒內的影片歸屬該照片",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.pairing_tip.pack(side="left", padx=10)
        
        # 壓縮設定區
        compress_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        compress_frame.pack(fill="x", padx=10, pady=8)
        
        # 壓縮開關
        self.compress_switch = ctk.CTkSwitch(
            compress_frame,
            text="壓縮輸出",
            variable=self.compress_enabled,
            command=self._on_compress_toggle,
            onvalue=True,
            offvalue=False
        )
        self.compress_switch.pack(side="left")
        
        # 壓縮品質選擇
        ctk.CTkLabel(compress_frame, text="  品質:", width=50).pack(side="left", padx=(20, 0))
        
        self.compress_dropdown = ctk.CTkOptionMenu(
            compress_frame,
            variable=self.compress_preset,
            values=list(COMPRESSION_PRESETS.keys()),
            width=180,
            state="disabled"
        )
        self.compress_dropdown.pack(side="left", padx=5)
        
        # 壓縮說明
        self.compress_info = ctk.CTkLabel(
            compress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.compress_info.pack(side="left", padx=10)
        

        
        # 預覽區標題
        preview_header = ctk.CTkFrame(left_frame, fg_color="transparent")
        preview_header.pack(fill="x", pady=(12, 5))
        
        ctk.CTkLabel(
            preview_header,
            text="配對預覽（可手動調整順序）",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        
        self.pair_count_label = ctk.CTkLabel(
            preview_header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.pair_count_label.pack(side="right")
        
        # 兩欄式預覽區
        preview_frame = ctk.CTkFrame(left_frame)
        preview_frame.pack(fill="both", expand=True, pady=5)
        
        # 左欄：照片列表
        photo_frame = ctk.CTkFrame(preview_frame)
        photo_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(photo_frame, text="📷 照片", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.photo_listbox = ctk.CTkScrollableFrame(photo_frame, height=180)
        self.photo_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 照片操作按鈕
        photo_btn_frame = ctk.CTkFrame(photo_frame, fg_color="transparent")
        photo_btn_frame.pack(pady=5)
        
        ctk.CTkButton(
            photo_btn_frame, text="🔼 上移", width=60,
            command=lambda: self._move_item("photo", -1)
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            photo_btn_frame, text="🔽 下移", width=60,
            command=lambda: self._move_item("photo", 1)
        ).pack(side="left", padx=2)
        
        # 右欄：影片列表
        video_frame = ctk.CTkFrame(preview_frame)
        video_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(video_frame, text="🎬 影片", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.video_listbox = ctk.CTkScrollableFrame(video_frame, height=180)
        self.video_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 影片操作按鈕
        video_btn_frame = ctk.CTkFrame(video_frame, fg_color="transparent")
        video_btn_frame.pack(pady=5)
        
        ctk.CTkButton(
            video_btn_frame, text="🔼 上移", width=60,
            command=lambda: self._move_item("video", -1)
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            video_btn_frame, text="🔽 下移", width=60,
            command=lambda: self._move_item("video", 1)
        ).pack(side="left", padx=2)
        
        # 儲存列表項目的選擇狀態
        self.photo_items = []  # [(MediaFile, CTkButton), ...]
        self.video_items = []  # [(MediaFile, CTkButton), ...]
        self.selected_photo_idx = None
        self.selected_video_idx = None
        
        # 進度條
        self.progress_bar = ctk.CTkProgressBar(left_frame)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(left_frame, text="就緒", font=ctk.CTkFont(size=12))
        self.status_label.pack()
    
    def _on_compress_toggle(self):
        """切換壓縮開關"""
        if self.compress_enabled.get():
            self.compress_dropdown.configure(state="normal")
            self.compress_info.configure(text="⚠️ 壓縮會花較長時間")
        else:
            self.compress_dropdown.configure(state="disabled")
            self.compress_info.configure(text="")

    def _on_pairing_mode_change(self, choice):
        """切換配對模式"""
        if choice == "時間比對":
            self.tolerance_label.pack(side="left", padx=(15, 0))
            self.tolerance_entry.pack(side="left", padx=5)
            self.tolerance_unit.pack(side="left")
            self.pairing_tip.configure(text="照片後 N 秒內的影片歸屬該照片")
        else:
            self.tolerance_label.pack_forget()
            self.tolerance_entry.pack_forget()
            self.tolerance_unit.pack_forget()
            if choice == "順序配對":
                self.pairing_tip.configure(text="按檔名排序配對（適用 LINE 檔案）")
            else:
                self.pairing_tip.configure(text="用圖像相似度配對")
    
    def _on_format_change(self, choice):
        """更新格式預覽並控制自訂輸入框狀態"""
        # 根據選擇啟用或禁用自訂前綴輸入框
        if choice == "自訂內容_序號":
            self.prefix_entry.configure(state="normal")
        else:
            self.prefix_entry.configure(state="disabled")
        
        # 更新預覽
        example = self._generate_filename(
            name="",
            seq=1,
            date=datetime.now(),
            ext=".jpg"
        )
        self.format_preview.configure(text=f"預覽: {example}")
    
    def _generate_filename(self, name: str, seq: int, date: datetime, ext: str, sub_seq: str = '') -> str:
        """根據選擇的格式生成檔名"""
        format_choice = self.naming_format.get()
        seq_str = f"{seq:03d}{sub_seq}"  # 如 001a, 001b
        
        if format_choice == "自訂內容_序號":
            prefix = self.custom_prefix.get().strip()
            if prefix:
                filename = f"{prefix}_{seq_str}"
            else:
                filename = seq_str  # 如果沒填自訂內容，只用序號
        else:
            # 序號模式
            filename = seq_str
        
        return f"{filename}{ext}"
    
    def _select_input(self):
        folder = filedialog.askdirectory(title="選擇輸入資料夾")
        if folder:
            self.input_dir.set(folder)
            # 自動設定輸出資料夾
            if not self.output_dir.get():
                self.output_dir.set(str(Path(folder).parent / "output"))
    
    def _select_output(self):
        folder = filedialog.askdirectory(title="選擇輸出資料夾")
        if folder:
            self.output_dir.set(folder)
    
    def _preview(self):
        input_path = self.input_dir.get()
        if not input_path:
            messagebox.showwarning("提示", "請先選擇輸入資料夾")
            return
        
        if not Path(input_path).exists():
            messagebox.showerror("錯誤", f"資料夾不存在: {input_path}")
            return
        
        self.status_label.configure(text="掃描中...")
        self.preview_btn.configure(state="disabled")
        
        def do_preview():
            try:
                files = scan_media_files(input_path)
                
                # 分離照片和影片
                self.photos = [f for f in files if not f.is_video]
                self.videos = [f for f in files if f.is_video]
                
                # 根據選擇的模式排序
                mode = self.pairing_mode.get()
                if mode == "順序配對":
                    # 照片按檔名排序，影片按下載時間排序
                    self.photos.sort(key=lambda x: x.path.name)
                    self.videos.sort(key=lambda x: x.path.stat().st_birthtime)
                elif mode == "時間比對":
                    # 都按時間排序
                    self.photos.sort(key=lambda x: x.created_time)
                    self.videos.sort(key=lambda x: x.created_time)
                else:
                    # 圖像比對：按檔名排序
                    self.photos.sort(key=lambda x: x.path.name)
                    self.videos.sort(key=lambda x: x.path.name)
                
                # 在主線程更新 UI
                self.after(0, self._update_preview_lists)
                
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("錯誤", f"掃描失敗: {e}"))
                self.after(0, lambda: self.status_label.configure(text="掃描失敗"))
            finally:
                self.after(0, lambda: self.preview_btn.configure(state="normal"))
        
        threading.Thread(target=do_preview, daemon=True).start()
    
    def _update_preview_lists(self):
        """更新兩欄縮圖網格顯示"""
        # 清空現有列表
        for widget in self.photo_listbox.winfo_children():
            widget.destroy()
        for widget in self.video_listbox.winfo_children():
            widget.destroy()
        
        self.photo_items = []
        self.video_items = []
        self.photo_thumbnails = []  # 保存縮圖引用避免被 GC
        self.video_thumbnails = []
        self.selected_photo_idx = None
        self.selected_video_idx = None
        
        # 縮圖尺寸
        thumb_size = (60, 80)
        cols = 4  # 每行顯示的縮圖數
        
        # 填充照片縮圖
        self.status_label.configure(text="生成照片縮圖中...")
        self.update()
        
        for i, photo in enumerate(self.photos):
            row = i // cols
            col = i % cols
            
            # 生成縮圖
            thumb_bytes = generate_thumbnail(photo.path, is_video=False, size=thumb_size)
            
            frame = ctk.CTkFrame(self.photo_listbox, fg_color="transparent")
            frame.grid(row=row, column=col, padx=2, pady=2)
            
            if thumb_bytes:
                # 轉換為 CTkImage
                pil_image = Image.open(io.BytesIO(thumb_bytes))
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=thumb_size)
                self.photo_thumbnails.append(ctk_image)
                
                btn = ctk.CTkButton(
                    frame,
                    image=ctk_image,
                    text=f"{i+1}",
                    compound="top",
                    width=70,
                    height=100,
                    fg_color="transparent",
                    hover_color=("gray70", "gray30"),
                    command=lambda idx=i: self._select_photo(idx)
                )
            else:
                btn = ctk.CTkButton(
                    frame,
                    text=f"{i+1}\n📷",
                    width=70,
                    height=100,
                    fg_color="transparent",
                    hover_color=("gray70", "gray30"),
                    command=lambda idx=i: self._select_photo(idx)
                )
            
            # 綁定雙擊事件打開檔案
            btn.bind("<Double-Button-1>", lambda e, idx=i: self._open_file(self.photos[idx].path))
            # 綁定滑鼠進入事件顯示大圖
            btn.bind("<Enter>", lambda e, idx=i: self._show_large_preview(self.photos[idx].path, is_video=False))
            btn.pack()
            self.photo_items.append((photo, btn))
        
        # 填充影片縮圖
        self.status_label.configure(text="生成影片縮圖中...")
        self.update()
        
        for i, video in enumerate(self.videos):
            row = i // cols
            col = i % cols
            
            # 生成縮圖
            thumb_bytes = generate_thumbnail(video.path, is_video=True, size=thumb_size)
            
            frame = ctk.CTkFrame(self.video_listbox, fg_color="transparent")
            frame.grid(row=row, column=col, padx=2, pady=2)
            
            if thumb_bytes:
                # 轉換為 CTkImage
                pil_image = Image.open(io.BytesIO(thumb_bytes))
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=thumb_size)
                self.video_thumbnails.append(ctk_image)
                
                btn = ctk.CTkButton(
                    frame,
                    image=ctk_image,
                    text=f"{i+1}",
                    compound="top",
                    width=70,
                    height=100,
                    fg_color="transparent",
                    hover_color=("gray70", "gray30"),
                    command=lambda idx=i: self._select_video(idx)
                )
            else:
                btn = ctk.CTkButton(
                    frame,
                    text=f"{i+1}\n🎬",
                    width=70,
                    height=100,
                    fg_color="transparent",
                    hover_color=("gray70", "gray30"),
                    command=lambda idx=i: self._select_video(idx)
                )
            
            # 綁定雙擊事件打開檔案
            btn.bind("<Double-Button-1>", lambda e, idx=i: self._open_file(self.videos[idx].path))
            # 綁定滑鼠進入事件顯示大圖
            btn.bind("<Enter>", lambda e, idx=i: self._show_large_preview(self.videos[idx].path, is_video=True))
            btn.pack()
            self.video_items.append((video, btn))
        
        # 更新配對數量
        count = min(len(self.photos), len(self.videos))
        self.pair_count_label.configure(
            text=f"{len(self.photos)} 張照片 / {len(self.videos)} 部影片 → {count} 組配對"
        )
        
        # 建立配對
        self._build_pairs()
        
        self.status_label.configure(text=f"預覽完成：{count} 組配對（單擊選擇交換，雙擊打開檔案）")
    
    def _select_photo(self, idx):
        """選擇照片 - 如果已選中另一張則交換位置"""
        if self.selected_photo_idx is not None and self.selected_photo_idx != idx:
            # 已有選中項目且不是自己，執行交換
            old_idx = self.selected_photo_idx
            self.photos[old_idx], self.photos[idx] = self.photos[idx], self.photos[old_idx]
            self.selected_photo_idx = None
            self._update_preview_lists()
            self._build_pairs()
            return
        
        # 取消之前的選擇
        if self.selected_photo_idx is not None and self.selected_photo_idx < len(self.photo_items):
            _, old_btn = self.photo_items[self.selected_photo_idx]
            old_btn.configure(fg_color="transparent")
        
        # 設定新選擇（或取消選擇）
        if self.selected_photo_idx == idx:
            self.selected_photo_idx = None  # 再次點擊取消選擇
        else:
            self.selected_photo_idx = idx
            _, btn = self.photo_items[idx]
            btn.configure(fg_color=("#3B8ED0", "#1F6AA5"))  # 藍色高亮
    
    def _select_video(self, idx):
        """選擇影片 - 如果已選中另一個則交換位置"""
        if self.selected_video_idx is not None and self.selected_video_idx != idx:
            # 已有選中項目且不是自己，執行交換
            old_idx = self.selected_video_idx
            self.videos[old_idx], self.videos[idx] = self.videos[idx], self.videos[old_idx]
            self.selected_video_idx = None
            self._update_preview_lists()
            self._build_pairs()
            return
        
        # 取消之前的選擇
        if self.selected_video_idx is not None and self.selected_video_idx < len(self.video_items):
            _, old_btn = self.video_items[self.selected_video_idx]
            old_btn.configure(fg_color="transparent")
        
        # 設定新選擇（或取消選擇）
        if self.selected_video_idx == idx:
            self.selected_video_idx = None  # 再次點擊取消選擇
        else:
            self.selected_video_idx = idx
            _, btn = self.video_items[idx]
            btn.configure(fg_color=("#3B8ED0", "#1F6AA5"))  # 藍色高亮
    
    def _open_file(self, file_path):
        """使用系統預設程式打開檔案"""
        try:
            subprocess.run(["open", str(file_path)], check=True)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法打開檔案: {e}")
    
    def _show_large_preview(self, file_path, is_video=False):
        """在大型預覽區顯示檔案預覽"""
        try:
            # 生成較大的縮圖
            large_size = (400, 300)
            thumb_bytes = generate_thumbnail(file_path, is_video=is_video, size=large_size)
            
            if thumb_bytes:
                pil_image = Image.open(io.BytesIO(thumb_bytes))
                # 保持比例縮放
                pil_image.thumbnail(large_size, Image.Resampling.LANCZOS)
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
                self.large_preview_image = ctk_image  # 避免 GC
                
                self.large_preview_label.configure(image=ctk_image, text="")
            else:
                self.large_preview_label.configure(image=None, text="無法預覽")
            
            # 顯示檔案名稱和類型
            filename = Path(file_path).name
            file_type = "🎬 影片" if is_video else "📷 照片"
            self.preview_filename_label.configure(text=f"{file_type}\n{filename}\n\n（雙擊縮圖可用系統程式開啟）")
            
        except Exception as e:
            self.large_preview_label.configure(image=None, text="預覽失敗")
            self.preview_filename_label.configure(text=str(e))
    
    def _move_item(self, item_type: str, direction: int):
        """移動選中的項目"""
        if item_type == "photo":
            idx = self.selected_photo_idx
            items = self.photos
        else:
            idx = self.selected_video_idx
            items = self.videos
        
        if idx is None:
            messagebox.showinfo("提示", f"請先選擇要移動的{'照片' if item_type == 'photo' else '影片'}")
            return
        
        new_idx = idx + direction
        if 0 <= new_idx < len(items):
            # 交換
            items[idx], items[new_idx] = items[new_idx], items[idx]
            
            # 更新選擇
            if item_type == "photo":
                self.selected_photo_idx = new_idx
            else:
                self.selected_video_idx = new_idx
            
            # 重新顯示列表
            self._update_preview_lists()
            
            # 恢復選擇狀態
            if item_type == "photo":
                self._select_photo(new_idx)
            else:
                self._select_video(new_idx)
    
    def _build_pairs(self):
        """根據當前照片/影片順序建立配對"""
        self.pairs = []
        for i, (photo, video) in enumerate(zip(self.photos, self.videos), 1):
            pair = FilePair(photo=photo, video=video, sequence=i)
            self.pairs.append(pair)
    
    def _run(self):
        if self.is_processing:
            return
        
        if not self.pairs:
            # 沒有預覽過，先執行預覽
            input_path = self.input_dir.get()
            if not input_path:
                messagebox.showwarning("提示", "請先選擇輸入資料夾")
                return
            
            # 同步執行預覽（簡化版）
            self.status_label.configure(text="掃描配對中...")
            self.update()
            try:
                files = scan_media_files(input_path)
                self.photos = [f for f in files if not f.is_video]
                self.videos = [f for f in files if f.is_video]
                
                # 按順序配對
                self.photos.sort(key=lambda x: x.path.name)
                self.videos.sort(key=lambda x: x.path.stat().st_birthtime)
                self._build_pairs()
            except Exception as e:
                messagebox.showerror("錯誤", f"配對失敗: {e}")
                return
            
            if not self.pairs:
                messagebox.showwarning("提示", "沒有找到可配對的檔案")
                return
        
        output_path = self.output_dir.get()
        if not output_path:
            messagebox.showwarning("提示", "請選擇輸出資料夾")
            return
        
        # 確認
        msg = f"即將處理 {len(self.pairs)} 組檔案\n"
        msg += f"命名格式: {self.naming_format.get()}\n"
        if self.compress_enabled.get():
            msg += f"壓縮品質: {self.compress_preset.get()}\n"
            msg += "⚠️ 壓縮會花較長時間\n"
        msg += f"輸出到: {output_path}\n\n繼續？"
        
        if not messagebox.askyesno("確認", msg):
            return
        
        self.is_processing = True
        self.run_btn.configure(state="disabled")
        self.preview_btn.configure(state="disabled")
        
        # 取得壓縮設定
        do_compress = self.compress_enabled.get()
        image_quality = 75  # 預設值
        video_crf = 28  # 預設值
        if do_compress:
            preset = COMPRESSION_PRESETS[self.compress_preset.get()]
            image_quality = preset["image_quality"]
            video_crf = preset["video_crf"]
        
        def do_process():
            try:
                output_dir = Path(output_path)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                total = len(self.pairs)
                success = 0
                ocr_failed = 0
                errors = []
                total_original_size = 0
                total_output_size = 0
                
                for i, pair in enumerate(self.pairs):
                    try:
                        # 更新進度 (thread-safe)
                        progress = (i + 1) / total
                        self.after(0, lambda p=progress: self.progress_bar.set(p))
                        
                        if do_compress:
                            self.after(0, lambda v=pair.video.path.name, n=i+1, t=total: 
                                self.status_label.configure(text=f"壓縮中 {n}/{t}: {v}"))
                        else:
                            self.after(0, lambda p=pair.photo.path.name, n=i+1, t=total:
                                self.status_label.configure(text=f"處理中 {n}/{t}: {p}"))
                        
                        # OCR 提取姓名
                        name = extract_name_from_image(pair.photo.path)
                        if not name:
                            name = extract_name_fullpage(pair.photo.path)
                        if not name:
                            name = f"UNKNOWN"
                            ocr_failed += 1
                        
                        # 使用照片時間作為日期
                        photo_date = pair.photo.created_time
                        
                        # 記錄原始大小
                        original_photo_size = get_file_size_mb(pair.photo.path)
                        original_video_size = get_file_size_mb(pair.video.path)
                        total_original_size += original_photo_size + original_video_size
                        
                        # 生成新檔名（取得子序號供 1:N 配對使用）
                        sub = getattr(pair, 'sub_sequence', '')
                        
                        if do_compress:
                            new_photo_name = self._generate_filename(name, pair.sequence, photo_date, ".jpg", "")
                            new_video_name = self._generate_filename(name, pair.sequence, photo_date, ".mp4", sub)
                        else:
                            photo_ext = pair.photo.path.suffix.lower()
                            video_ext = pair.video.path.suffix.lower()
                            new_photo_name = self._generate_filename(name, pair.sequence, photo_date, photo_ext, "")
                            new_video_name = self._generate_filename(name, pair.sequence, photo_date, video_ext, sub)
                        
                        new_photo = output_dir / new_photo_name
                        new_video = output_dir / new_video_name
                        
                        # 照片只輸出一次
                        if not new_photo.exists():
                            if do_compress:
                                compress_image(pair.photo.path, new_photo, quality=image_quality)
                            else:
                                shutil.copy2(pair.photo.path, new_photo)
                        
                        # 取得影片分割設定
                        split_count = get_segment_count_from_option(self.video_split_count.get())
                        
                        # 影片處理
                        if split_count > 1:
                            # 需要分割影片
                            self.after(0, lambda v=pair.video.path.name, n=i+1, t=total, s=split_count:
                                self.status_label.configure(text=f"分割影片 {n}/{t}: {v} ({s} 段)"))
                            
                            # 生成基礎檔名（包含 1:N 配對的子序號）
                            # 例如：1:N 配對的 001a 影片分割後會是 001a_1, 001a_2, 001a_3...
                            base_video_name = self._generate_filename("", pair.sequence, photo_date, "", "")
                            base_video_name = base_video_name.rstrip(".")  # 移除尾端的點
                            if sub:
                                base_video_name = f"{base_video_name}{sub}"  # 加上 1:N 的子序號
                            
                            video_ext = ".mp4" if do_compress else pair.video.path.suffix.lower()
                            crf_value = video_crf if do_compress else 18
                            
                            split_files = split_video(
                                input_path=pair.video.path,
                                output_dir=output_dir,
                                num_segments=split_count,
                                base_name=base_video_name,
                                ext=video_ext,
                                compress=do_compress,
                                crf=crf_value
                            )
                            
                            # 檢查分割是否成功
                            if not split_files:
                                errors.append(f"{pair.video.path.name}: 影片分割失敗")
                                continue
                            
                            # 計算分割後檔案大小
                            for sf in split_files:
                                if sf.exists():
                                    total_output_size += get_file_size_mb(sf)
                        else:
                            # 不分割，直接輸出
                            if do_compress:
                                if not compress_video(pair.video.path, new_video, crf=video_crf):
                                    shutil.copy2(pair.video.path, new_video.with_suffix(pair.video.path.suffix.lower()))
                            else:
                                shutil.copy2(pair.video.path, new_video)
                        
                        # 計算輸出大小
                        if new_photo.exists():
                            total_output_size += get_file_size_mb(new_photo)
                        if new_video.exists():
                            total_output_size += get_file_size_mb(new_video)
                        
                        success += 1
                        

                    except Exception as e:
                        errors.append(f"{pair.photo.path.name}: {e}")
                
                # 完成
                self.progress_bar.set(1)
                
                result_msg = f"處理完成！\n\n"
                result_msg += f"✅ 成功: {success} 組\n"
                if ocr_failed:
                    result_msg += f"⚠️ OCR 失敗（使用 UNKNOWN）: {ocr_failed} 組\n"
                if errors:
                    result_msg += f"❌ 錯誤: {len(errors)} 組\n"
                    for err in errors[:5]:
                        result_msg += f"   • {err}\n"
                
                if do_compress and total_original_size > 0:
                    reduction = (1 - total_output_size / total_original_size) * 100
                    result_msg += f"\n📦 原始大小: {total_original_size:.1f} MB\n"
                    result_msg += f"📦 輸出大小: {total_output_size:.1f} MB\n"
                    result_msg += f"📦 節省: {reduction:.1f}%\n"
                
                result_msg += f"\n輸出位置: {output_path}"
                
                messagebox.showinfo("完成", result_msg)
                self.status_label.configure(text=f"完成！成功處理 {success} 組")
                
            except Exception as e:
                messagebox.showerror("錯誤", f"處理失敗: {e}")
                self.status_label.configure(text="處理失敗")
            finally:
                self.is_processing = False
                self.run_btn.configure(state="normal")
                self.preview_btn.configure(state="normal")
        
        threading.Thread(target=do_process, daemon=True).start()


def main():
    app = RitualRenamerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
