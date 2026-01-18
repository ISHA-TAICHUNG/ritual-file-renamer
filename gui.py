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

from src.ocr import extract_name_from_image, extract_name_fullpage
from src.pairing import scan_media_files, pair_files, FilePair
from src.compress import compress_image, compress_video, get_file_size_mb, COMPRESSION_PRESETS
from src.video_split import split_video, get_segment_count_from_option


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
        self.geometry("800x750")
        self.minsize(700, 650)
        
        # 狀態變數
        self.input_dir = ctk.StringVar()
        self.output_dir = ctk.StringVar()
        self.naming_format = ctk.StringVar(value="序號")
        self.custom_prefix = ctk.StringVar(value="")  # 自訂前綴
        self.pairing_mode = ctk.StringVar(value="圖像比對（推薦）")
        self.compress_enabled = ctk.BooleanVar(value=False)
        self.compress_preset = ctk.StringVar(value="平衡（推薦）")
        self.video_split_count = ctk.StringVar(value="不分割")  # 影片分割段數
        self.pairs = []
        self.is_processing = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        # 主容器
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 標題
        title_label = ctk.CTkLabel(
            main_frame,
            text="🕯️ 法事檔案自動配對命名工具",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 設定區
        settings_frame = ctk.CTkFrame(main_frame)
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
            values=["圖像比對（推薦）", "順序配對", "時間配對"],
            width=150
        )
        pairing_dropdown.pack(side="left", padx=5)
        
        # 配對模式說明
        ctk.CTkLabel(
            pairing_frame,
            text="比對照片與影片內容自動配對",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(side="left", padx=10)
        
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
        
        # 預覽區
        preview_label = ctk.CTkLabel(main_frame, text="配對預覽", font=ctk.CTkFont(size=16, weight="bold"))
        preview_label.pack(pady=(12, 5), anchor="w")
        
        self.preview_text = ctk.CTkTextbox(main_frame, height=230, font=ctk.CTkFont(family="Menlo", size=12))
        self.preview_text.pack(fill="both", expand=True, pady=5)
        self.preview_text.insert("1.0", "選擇輸入資料夾後點擊「預覽」查看配對結果...")
        self.preview_text.configure(state="disabled")
        
        # 進度條
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(main_frame, text="就緒", font=ctk.CTkFont(size=12))
        self.status_label.pack()
        
        # 按鈕區
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=12)
        
        self.preview_btn = ctk.CTkButton(
            button_frame,
            text="👁️ 預覽",
            width=120,
            height=40,
            command=self._preview
        )
        self.preview_btn.pack(side="left", padx=10)
        
        self.run_btn = ctk.CTkButton(
            button_frame,
            text="▶️ 執行",
            width=120,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            command=self._run
        )
        self.run_btn.pack(side="left", padx=10)
    
    def _on_compress_toggle(self):
        """切換壓縮開關"""
        if self.compress_enabled.get():
            self.compress_dropdown.configure(state="normal")
            self.compress_info.configure(text="⚠️ 壓縮會花較長時間")
        else:
            self.compress_dropdown.configure(state="disabled")
            self.compress_info.configure(text="")
    
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
                
                # 取得配對模式
                pairing_choice = self.pairing_mode.get()
                if '圖像' in pairing_choice:
                    mode = 'image'
                elif '順序' in pairing_choice:
                    mode = 'order'
                else:
                    mode = 'time'
                self.pairs = pair_files(files, mode=mode)
                
                # 更新預覽
                self.preview_text.configure(state="normal")
                self.preview_text.delete("1.0", "end")
                
                if not self.pairs:
                    self.preview_text.insert("1.0", "沒有找到可配對的檔案\n")
                else:
                    photos = [f for f in files if not f.is_video]
                    videos = [f for f in files if f.is_video]
                    
                    # 計算總大小
                    total_size = sum(get_file_size_mb(p.photo.path) + get_file_size_mb(p.video.path) for p in self.pairs)
                    
                    summary = f"找到 {len(photos)} 張照片、{len(videos)} 部影片\n"
                    summary += f"成功配對 {len(self.pairs)} 組（總計 {total_size:.1f} MB）\n"
                    summary += f"命名格式: {self.naming_format.get()}\n"
                    if self.compress_enabled.get():
                        summary += f"壓縮: {self.compress_preset.get()}\n"
                    summary += "=" * 50 + "\n\n"
                    
                    for pair in self.pairs:
                        photo_size = get_file_size_mb(pair.photo.path)
                        video_size = get_file_size_mb(pair.video.path)
                        
                        summary += f"[{pair.sequence:03d}]\n"
                        summary += f"  📷 {pair.photo.path.name} ({photo_size:.1f} MB)\n"
                        summary += f"     時間: {pair.photo.created_time} [{pair.photo.time_source}]\n"
                        summary += f"  🎬 {pair.video.path.name} ({video_size:.1f} MB)\n"
                        summary += f"     時間: {pair.video.created_time} [{pair.video.time_source}]\n\n"
                    
                    self.preview_text.insert("1.0", summary)
                
                self.preview_text.configure(state="disabled")
                self.status_label.configure(text=f"預覽完成：{len(self.pairs)} 組配對")
                
            except Exception as e:
                messagebox.showerror("錯誤", f"掃描失敗: {e}")
                self.status_label.configure(text="掃描失敗")
            finally:
                self.preview_btn.configure(state="normal")
        
        threading.Thread(target=do_preview, daemon=True).start()
    
    def _run(self):
        if self.is_processing:
            return
        
        if not self.pairs:
            messagebox.showwarning("提示", "請先預覽配對結果")
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
                        # 更新進度
                        progress = (i + 1) / total
                        self.progress_bar.set(progress)
                        
                        if do_compress:
                            self.status_label.configure(text=f"壓縮中 {i+1}/{total}: {pair.video.path.name}")
                        else:
                            self.status_label.configure(text=f"處理中 {i+1}/{total}: {pair.photo.path.name}")
                        
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
                        
                        # 生成新檔名
                        sub = getattr(pair, 'sub_sequence', '')
                        
                        # 照片檔名（不帶子序號，同一張照片只輸出一次）
                        photo_key = (pair.photo.path, pair.sequence)
                        
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
                        
                        # 取得此配對的子序號（1:N 配對時會有 a, b, c...）
                        pair_sub = getattr(pair, 'sub_sequence', '')
                        
                        # 影片處理
                        if split_count > 1:
                            # 需要分割影片
                            self.status_label.configure(text=f"分割影片 {i+1}/{total}: {pair.video.path.name} ({split_count} 段)")
                            
                            # 生成基礎檔名（包含 1:N 配對的子序號）
                            # 例如：1:N 配對的 001a 影片分割後會是 001a_1, 001a_2, 001a_3...
                            base_video_name = self._generate_filename("", pair.sequence, photo_date, "", "")
                            base_video_name = base_video_name.rstrip(".")  # 移除尾端的點
                            if pair_sub:
                                base_video_name = f"{base_video_name}{pair_sub}"  # 加上 1:N 的子序號
                            
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
