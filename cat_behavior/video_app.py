import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import cv2
from PIL import Image, ImageTk
from ultralytics import YOLO
from datetime import datetime
import os
import hashlib
from database_manager import DatabaseManager

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Phân Tích Video Mèo - Video Import")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f5f6fa")

        # --- Tải Model ---
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'runs', 'detect', 'cat_behavior_v1', 'weights', 'best.pt')
        try:
            self.model = YOLO(model_path)
            print(f"Đã tải model từ: {model_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không tìm thấy model tại: {model_path}")
            self.root.destroy()

        # --- Kết nối Database ---
        # LƯU Ý: THAY ĐỔI PASSWORD CỦA BẠN TẠI ĐÂY
        self.db = DatabaseManager(password="") 
        
        success, msg = self.db.test_connection()
        if not success:
            messagebox.showwarning("Cảnh báo Database", msg + "\nDữ liệu sẽ không được lưu.")
        else:
            print("Hệ thống: " + msg)

        # --- Biến trạng thái ---
        self.cap = None
        self.is_running = False
        self.is_paused = False
        self.video_path = None
        self.current_video_id = None
        
        self.last_behavior_raw = None
        self.event_start_time = 0
        self.conf_list = []

        self.setup_ui()

    def setup_ui(self):
        header = tk.Label(self.root, text="PHÂN TÍCH HÀNH VI QUA VIDEO FILE", 
                         font=("Helvetica", 22, "bold"), bg="#f5f6fa", fg="#2f3640")
        header.pack(pady=20)

        main_content = tk.Frame(self.root, bg="#f5f6fa")
        main_content.pack(fill=tk.BOTH, expand=True, padx=20)

        left_panel = tk.Frame(main_content, bg="black", width=640, height=480)
        left_panel.pack(side=tk.LEFT, padx=10)
        left_panel.pack_propagate(False)

        self.video_label = tk.Label(left_panel, bg="black")
        self.video_label.pack(expand=True, fill=tk.BOTH)

        right_panel = tk.Frame(main_content, bg="#f5f6fa")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(right_panel, text="KẾT QUẢ PHÂN TÍCH (LƯU DB)", font=("Helvetica", 12, "bold"), bg="#f5f6fa").pack(pady=(0, 5))

        self.log_box = scrolledtext.ScrolledText(right_panel, width=30, height=15, 
                                                font=("Segoe UI", 10), bg="white")
        self.log_box.pack(pady=5, fill=tk.BOTH, expand=True)

        btn_panel = tk.Frame(right_panel, bg="#f5f6fa")
        btn_panel.pack(pady=10)

        tk.Button(btn_panel, text="📁 CHỌN VIDEO", font=("Helvetica", 11, "bold"), 
                  bg="#f39c12", fg="white", width=18, height=1, command=self.import_video).pack(pady=5)

        self.btn_play = tk.Button(btn_panel, text="▶ PHÁT & PHÂN TÍCH", font=("Helvetica", 11, "bold"), 
                                  bg="#44bd32", fg="white", width=18, height=1, command=self.play_video)
        self.btn_play.pack(pady=5)
        self.btn_play.config(state=tk.DISABLED)

        self.btn_pause = tk.Button(btn_panel, text="⏸ TẠM DỪNG", font=("Helvetica", 11, "bold"), 
                                  bg="#e67e22", fg="white", width=18, height=1, command=self.toggle_pause)
        self.btn_pause.pack(pady=5)
        self.btn_pause.config(state=tk.DISABLED)

        tk.Button(btn_panel, text="📜 XEM LỊCH SỬ (DB)", font=("Helvetica", 11, "bold"), 
                  bg="#9b59b6", fg="white", width=18, height=1, command=self.show_history).pack(pady=5)

    def write_log(self, message):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{current_time}] {message}\n")
        self.log_box.see(tk.END)

    def get_video_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def import_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        if file_path:
            self.video_path = file_path
            v_hash = self.get_video_hash(file_path)
            
            # Kiểm tra xem video đã có trong DB chưa
            video_rec = self.db.get_video_by_hash(v_hash)
            if video_rec:
                self.current_video_id = video_rec['id']
                self.write_log(f"Video đã tồn tại trong DB (ID: {self.current_video_id})")
            else:
                cap = cv2.VideoCapture(file_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                
                self.current_video_id = self.db.insert_video(
                    os.path.basename(file_path), file_path, v_hash, duration
                )
                self.write_log(f"Đã đăng ký video mới (ID: {self.current_video_id})")

            self.btn_play.config(state=tk.NORMAL)
            self.write_log(f"Sẵn sàng phân tích: {os.path.basename(file_path)}")

    def play_video(self):
        if self.video_path:
            self.cap = cv2.VideoCapture(self.video_path)
            self.is_running = True
            self.is_paused = False
            self.btn_play.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            
            # Reset trạng thái nhận diện cho video mới
            self.last_behavior_raw = None
            self.event_start_time = 0
            self.conf_list = []
            
            self.write_log("Đang phân tích khung hình...")
            self.update_frame()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text="▶ TIẾP TỤC" if self.is_paused else "⏸ TẠM DỪNG")

    def update_frame(self):
        if self.is_running and self.cap and not self.is_paused:
            ret, frame = self.cap.read()
            if ret:
                results = self.model(frame, verbose=False, conf=0.5)
                
                # Lấy giây hiện tại trong video
                current_v_time = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                
                current_behavior_raw = None
                current_conf = 0
                
                if len(results[0].boxes) > 0:
                    box = results[0].boxes[0]
                    current_conf = float(box.conf[0])
                    class_id = int(box.cls[0])
                    current_behavior_raw = self.model.names[class_id]

                # LOGIC LƯU DATABASE: Khi đổi trạng thái
                if current_behavior_raw != self.last_behavior_raw:
                    # 1. Lưu hành vi cũ vừa kết thúc
                    if self.last_behavior_raw and self.current_video_id:
                        avg_conf = sum(self.conf_list)/len(self.conf_list) if self.conf_list else 0
                        self.db.insert_behavior_event(
                            self.current_video_id, self.last_behavior_raw, 
                            self.event_start_time, current_v_time, avg_conf
                        )
                        self.write_log(f"Ghi DB: {self.last_behavior_raw} ({self.event_start_time:.1f}s -> {current_v_time:.1f}s)")
                    
                    # 2. Chuyển sang hành vi mới
                    self.last_behavior_raw = current_behavior_raw
                    self.event_start_time = current_v_time
                    self.conf_list = [current_conf] if current_behavior_raw else []
                else:
                    # Đang duy trì hành vi cũ, gom confidence
                    if current_behavior_raw:
                        self.conf_list.append(current_conf)

                # Hiển thị
                annotated_frame = results[0].plot()
                img = cv2.resize(annotated_frame, (640, 480))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img_tk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = img_tk
                self.video_label.configure(image=img_tk)
                
                self.root.after(1, self.update_frame)
            else:
                # Video kết thúc -> Lưu hành vi cuối cùng còn đang dang dở
                if self.last_behavior_raw and self.current_video_id:
                    end_time = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                    avg_conf = sum(self.conf_list)/len(self.conf_list) if self.conf_list else 0
                    self.db.insert_behavior_event(
                        self.current_video_id, self.last_behavior_raw, 
                        self.event_start_time, end_time, avg_conf
                    )
                
                self.write_log("✅ Hoàn thành phân tích toàn bộ video.")
                self.is_running = False
                self.cap.release()
                self.btn_play.config(state=tk.NORMAL)
                self.btn_pause.config(state=tk.DISABLED)

    def show_history(self):
        win = tk.Toplevel(self.root)
        win.title("Lịch sử Hoạt động của Mèo")
        win.geometry("900x500")
        
        cols = ("Video", "Hành vi", "Bắt đầu", "Kết thúc", "Độ tin cậy")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        data = self.db.get_history()
        for r in data:
            tree.insert("", tk.END, values=(
                r['file_name'], r['behavior_name'], 
                f"{r['start_time']:.1f}s", f"{r['end_time']:.1f}s", 
                f"{r['confidence']*100:.1f}%"
            ))
        
        scrollbar = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()
