import asyncio
import edge_tts
import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime

# ================= CẤU HÌNH MẶC ĐỊNH =================
DEFAULT_VOICE = "vi-VN-HoaiMyNeural"
CHUNK_SIZE = 2000
CONCURRENT_REQUESTS = 5
TEMP_DIR = "temp_audio_chunks"
# =====================================================

class TextToSpeechApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Edge - Text to Speech")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        

        # Biến lưu trữ đường dẫn
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.voice_var = tk.StringVar(value=DEFAULT_VOICE)
        self.rate_var = tk.StringVar(value="+0%")
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.progress_var = tk.DoubleVar(value=0)

        self.setup_ui()

    def setup_ui(self):
        # Frame chọn file
        paddy = 10
        frame_file = tk.LabelFrame(self.root, text="Cấu hình File", padx=10, pady=10)
        frame_file.pack(fill="x", padx=10, pady=5)

        # Input
        tk.Label(frame_file, text="File văn bản (.txt):").grid(row=0, column=0, sticky="w")
        tk.Entry(frame_file, textvariable=self.input_path, width=45).grid(row=0, column=1, padx=5)
        tk.Button(frame_file, text="Chọn...", command=self.browse_input).grid(row=0, column=2)

        # Output
        tk.Label(frame_file, text="Lưu file WAV tại:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(frame_file, textvariable=self.output_path, width=45).grid(row=1, column=1, padx=5)
        tk.Button(frame_file, text="Chọn...", command=self.browse_output).grid(row=1, column=2)

        # Frame cấu hình giọng
        frame_voice = tk.LabelFrame(self.root, text="Cấu hình Giọng đọc", padx=10, pady=10)
        frame_voice.pack(fill="x", padx=10, pady=5)

        # Voice selection
        voices = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural", "en-US-AriaNeural", "en-US-GuyNeural"]
        tk.Label(frame_voice, text="Giọng đọc:").grid(row=0, column=0, sticky="w")
        voice_cb = ttk.Combobox(frame_voice, textvariable=self.voice_var, values=voices, width=30, state="readonly")
        voice_cb.grid(row=0, column=1, padx=5, sticky="w")

        # Tốc độ (Đã sửa thành menu thả xuống)
        tk.Label(frame_voice, text="Tốc độ:").grid(row=1, column=0, sticky="w", pady=5)
        rate_values = ["-50%", "-25%", "-10%", "+0%", "+10%", "+25%", "+50%", "+75%", "+100%"]
        rate_cb = ttk.Combobox(frame_voice, textvariable=self.rate_var, values=rate_values, width=10, state="readonly")
        rate_cb.grid(row=1, column=1, padx=5, sticky="w")
        
        

        # Progress Area
        frame_progress = tk.Frame(self.root, padx=10, pady=10)
        frame_progress.pack(fill="x", padx=10)

        self.btn_run = tk.Button(frame_progress, text="BẮT ĐẦU CHUYỂN ĐỔI", command=self.start_thread, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_run.pack(fill="x", pady=(0, 10))

        tk.Label(frame_progress, textvariable=self.status_var, fg="blue").pack(anchor="w")
        self.progress_bar = ttk.Progressbar(frame_progress, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x")

        # Log Text Area (Optional)
        self.log_text = tk.Text(self.root, height=8, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)

    # --- Các hàm GUI Helper ---
    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if filename:
            self.input_path.set(filename)
            # Tự động gợi ý tên file output
            base_name = os.path.splitext(filename)[0]
            self.output_path.set(base_name + ".wav")

    def browse_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Audio", "*.wav")])
        if filename:
            self.output_path.set(filename)

    def toggle_inputs(self, enable):
        state = "normal" if enable else "disabled"
        self.btn_run.config(state=state)
        # Có thể disable thêm các nút khác nếu cần

    # --- Logic Xử Lý (Threading & Async) ---
    def start_thread(self):
        if not self.input_path.get() or not self.output_path.get():
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn file Input và nơi lưu Output.")
            return
        
        # Kiểm tra ffmpeg
        if not self.check_ffmpeg():
            messagebox.showerror("Lỗi FFmpeg", "Không tìm thấy 'ffmpeg.exe'.\nVui lòng tải và đặt file ffmpeg.exe cùng thư mục với phần mềm này.")
            return

        self.toggle_inputs(False)
        self.progress_var.set(0)
        
        # Chạy logic nặng trong luồng riêng để không đơ GUI
        thread = threading.Thread(target=self.run_async_logic)
        thread.daemon = True
        thread.start()

    def check_ffmpeg(self):
        """Kiểm tra xem ffmpeg có tồn tại không"""
        # Kiểm tra file exe ngay tại thư mục hiện tại
        if os.path.isfile("ffmpeg.exe"):
            return "ffmpeg.exe"
        
        # Kiểm tra trong biến môi trường PATH
        if shutil.which("ffmpeg"):
            return "ffmpeg"
            
        return None

    def run_async_logic(self):
        try:
            asyncio.run(self.process_tts())
            messagebox.showinfo("Thành công", f"Đã xuất file thành công:\n{self.output_path.get()}")
        except Exception as e:
            self.log(f"LỖI: {str(e)}")
            messagebox.showerror("Lỗi", str(e))
        finally:
            self.root.after(0, lambda: self.toggle_inputs(True))
            self.status_var.set("Hoàn tất hoặc đã dừng.")

    # --- Core Logic TTS (Đã sửa đổi cho Class) ---
    def smart_split_text(self, text, max_length):
        text = re.sub(r'\n+', ' ', text).strip()
        sentences = re.split(r'(?<=[.!?]) +', text)
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > max_length:
                if current_chunk: chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence
        if current_chunk: chunks.append(current_chunk.strip())
        return chunks

    async def generate_chunk(self, text, index, semaphore, voice, rate):
        filename = os.path.join(TEMP_DIR, f"{index:05d}.mp3")
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return index

        async with semaphore:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(filename)
            return index

    async def process_tts(self):
        input_file = self.input_path.get()
        final_wav_output = self.output_path.get()
        # Tạo file mp3 tạm thời để merge trước khi convert sang wav
        temp_merged_mp3 = "temp_merged_output.mp3" 
        
        voice = self.voice_var.get()
        rate = self.rate_var.get()

        # 1. Chuẩn bị thư mục tạm
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        else:
            # Xóa file cũ trong temp để tránh lẫn lộn
            for f in os.listdir(TEMP_DIR):
                os.remove(os.path.join(TEMP_DIR, f))

        self.status_var.set("Đang đọc file và phân đoạn...")
        self.log("Đang đọc file input...")
        
        with open(input_file, "r", encoding="utf-8") as f:
            full_text = f.read()

        chunks = self.smart_split_text(full_text, CHUNK_SIZE)
        total_chunks = len(chunks)
        self.log(f"Tổng số đoạn: {total_chunks}")

        # 2. Tải các đoạn (Async)
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        tasks = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            tasks.append(self.generate_chunk(chunk, i, semaphore, voice, rate))

        completed = 0
        for future in asyncio.as_completed(tasks):
            await future
            completed += 1
            bar_percent = (completed / total_chunks) * 98
            self.progress_var.set(bar_percent)
            text_percent = int((completed / total_chunks) * 100)
            self.status_var.set(f"Đang tải audio: {completed}/{total_chunks} đoạn ({text_percent}%)")

        # 3. Ghép file MP3
        self.status_var.set("Đang ghép các file MP3 tạm...")
        self.log("Bắt đầu ghép file...")
        
        with open(temp_merged_mp3, "wb") as outfile:
            for i in range(len(chunks)):
                chunk_path = os.path.join(TEMP_DIR, f"{i:05d}.mp3")
                if os.path.exists(chunk_path):
                    with open(chunk_path, "rb") as infile:
                        shutil.copyfileobj(infile, outfile)

        self.progress_var.set(99)

        # 4. Convert MP3 sang WAV bằng FFmpeg
        self.status_var.set("Đang dùng FFmpeg chuyển đổi sang WAV...")
        self.log("Đang chạy FFmpeg...")
        
        ffmpeg_cmd = self.check_ffmpeg()
        
        # Lệnh: ffmpeg -y (overwrite) -i input.mp3 output.wav
        # Ẩn cửa sổ console khi chạy ffmpeg
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            subprocess.run(
                [ffmpeg_cmd, "-y", "-i", temp_merged_mp3, final_wav_output],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            self.log("Chuyển đổi WAV hoàn tất.")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Lỗi FFmpeg: {e}")

        # 5. Dọn dẹp
        self.status_var.set("Đang dọn dẹp file rác...")
        if os.path.exists(temp_merged_mp3):
            os.remove(temp_merged_mp3)
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)

        self.progress_var.set(100)
        self.log("Xử lý hoàn tất!")

# ================= MAIN =================
if __name__ == "__main__":
    root = tk.Tk()
    app = TextToSpeechApp(root)
    root.mainloop()