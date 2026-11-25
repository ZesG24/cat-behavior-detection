import tkinter as tk
from tkinter import scrolledtext, messagebox
import cv2
from PIL import Image, ImageTk
from ultralytics import YOLO
from datetime import datetime
import os

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Giám Sát Mèo - Real-time Camera")
        self.root.geometry("1100x700")
        self.root.configure(bg="#f5f6fa")

        # --- Tải Model ---
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'runs', 'detect', 'cat_behavior_v1', 'weights', 'best.pt')
        
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không tìm thấy model tại: {model_path}")
            self.root.destroy()

        self.cap = None
        self.is_running = False
        self.last_behavior = None

        self.setup_ui()

    def setup_ui(self):
        header = tk.Label(self.root, text="GIÁM SÁT QUA CAMERA (REAL-TIME)", 
                         font=("Helvetica", 22, "bold"), bg="#f5f6fa", fg="#2f3640")
        header.pack(pady=20)

        main_content = tk.Frame(self.root, bg="#f5f6fa")
        main_content.pack(fill=tk.BOTH, expand=True, padx=20)

        # Panel trái: Video
        left_panel = tk.Frame(main_content, bg="black", width=640, height=480)
        left_panel.pack(side=tk.LEFT, padx=10)
        left_panel.pack_propagate(False)

        self.video_label = tk.Label(left_panel, bg="black")
        self.video_label.pack(expand=True, fill=tk.BOTH)

        # Panel phải: Log & Control
        right_panel = tk.Frame(main_content, bg="#f5f6fa")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(right_panel, text="NHẬT KÝ HÀNH VI", font=("Helvetica", 12, "bold"), bg="#f5f6fa").pack(pady=(0, 5))

        self.log_box = scrolledtext.ScrolledText(right_panel, width=30, height=20, 
                                                font=("Segoe UI", 10), bg="white")
        self.log_box.pack(pady=5, fill=tk.BOTH, expand=True)

        btn_panel = tk.Frame(right_panel, bg="#f5f6fa")
        btn_panel.pack(pady=10)

        self.btn_start = tk.Button(btn_panel, text="▶ MỞ CAMERA", font=("Helvetica", 11, "bold"), 
                                  bg="#44bd32", fg="white", width=18, height=2, command=self.start_camera)
        self.btn_start.pack(pady=5)

        self.btn_stop = tk.Button(btn_panel, text="⏹ DỪNG", font=("Helvetica", 11, "bold"), 
                                 bg="#c23616", fg="white", width=18, height=2, command=self.stop_camera)
        self.btn_stop.pack(pady=5)
        self.btn_stop.config(state=tk.DISABLED)

    def write_log(self, message):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{current_time}] {message}\n")
        self.log_box.see(tk.END)

    def start_camera(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Lỗi", "Không tìm thấy Camera!")
                return
            self.is_running = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.write_log("Hệ thống: Bắt đầu giám sát...")
            self.update_frame()

    def stop_camera(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.config(image='')
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.last_behavior = None
        self.write_log("Hệ thống: Đã dừng camera.")

    def update_frame(self):
        if self.is_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (640, 480))
                results = self.model(frame, verbose=False)
                annotated_frame = results[0].plot()

                current_behavior = None
                if len(results[0].boxes) > 0:
                    conf = float(results[0].boxes[0].conf[0])
                    if conf >= 0.75:
                        class_id = int(results[0].boxes[0].cls[0])
                        label = self.model.names[class_id]
                        current_behavior = label

                if current_behavior != self.last_behavior:
                    if current_behavior:
                        vi_label = current_behavior.replace("cat_eating", "Mèo đang ăn")\
                                                   .replace("cat_sitting", "Mèo đang ngồi")\
                                                   .replace("cat_sleeping", "Mèo đang ngủ")\
                                                   .replace("cat_standing", "Mèo đang đứng")
                        self.write_log(f"Phát hiện: {vi_label}")
                    else:
                        self.write_log("Trạng thái: Không tìm thấy đối tượng")
                    self.last_behavior = current_behavior

                img = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img_tk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = img_tk
                self.video_label.configure(image=img_tk)
                
                self.root.after(10, self.update_frame)

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
