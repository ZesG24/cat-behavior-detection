import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont
from ultralytics import YOLO
from datetime import datetime
import os
import hashlib
from database_manager import DatabaseManager

# --- KÍCH HOẠT HIGH-DPI AWARENESS (ĐỘ SẮC NÉT) ---
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class CatBehaviorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Giám Sát Hành Vi Mèo - Cat Behavior AI Dashboard")
        self.root.geometry("1350x850")
        self.root.configure(bg="#090d16")  # Obsidian dark background

        # --- ĐỊNH NGHĨA HỆ THỐNG MÀU (DARK MODE PREMIUM) ---
        self.BG_MAIN = "#090d16"      # Obsidian Dark
        self.BG_CARD = "#131b2e"      # Slate Deep Blue
        self.BG_SIDEBAR = "#0b0f19"   # Slate Darkest
        self.BORDER_COLOR = "#1e293b" # Slate Border
        self.ACCENT_EMERALD = "#10b981"
        self.ACCENT_EMERALD_HOVER = "#059669"
        self.ACCENT_BLUE = "#3b82f6"
        self.ACCENT_BLUE_HOVER = "#2563eb"
        self.ACCENT_YELLOW = "#f59e0b"
        self.ACCENT_YELLOW_HOVER = "#d97706"
        self.ACCENT_RED = "#ef4444"
        self.ACCENT_RED_HOVER = "#dc2626"
        self.TXT_PRIMARY = "#f8fafc"
        self.TXT_SECONDARY = "#94a3b8"
        self.FONT_NAME = "Segoe UI"

        # --- TẠO ẢNH CHỜ STANDBY ---
        self.standby_image = self.create_standby_image()

        # --- ĐƯỜNG DẪN MODEL MỚI NHẤT ---
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'runs', 'detect', 'cat_behavior_v1', 'weights', 'best.pt')
        
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Không tìm thấy file model tại: {model_path}")
            self.model = YOLO(model_path)
            print(f"Successfully loaded model from: {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            messagebox.showerror("Lỗi", f"Không tìm thấy file model!\n\nĐường dẫn đã thử:\n{model_path}")

        # --- KẾT NỐI DATABASE ---
        self.db = DatabaseManager(password="") 
        success, msg = self.db.test_connection()
        if not success:
            messagebox.showwarning("Cảnh báo Database", f"Không thể kết nối cơ sở dữ liệu MySQL.\nChi tiết: {msg}\nDữ liệu phân tích video sẽ không được lưu.")
        else:
            print("System: Database connected successfully.")

        # --- BIẾN TRẠNG THÁI CAMERA & VIDEO ANALYSIS ---
        self.cap = None
        self.is_running = False
        self.last_behavior = None
        self.last_behavior_raw_db = None
        self.event_start_time = 0
        self.conf_list = []
        self.current_video_id = None
        self.is_video_mode = False
        self.is_paused = False

        # --- BIẾN TRẠNG THÁI CAMERA TRỰC TIẾP (LIVE SESSION) ---
        self.current_session_id = None
        self.last_cam_behavior_raw = None
        self.cam_event_start_dt = None
        self.cam_conf_list = []
        self.cam_ai_active = False

        # --- BIẾN TRẠNG THÁI VIDEO PLAYBACK (XEM LẠI) ---
        self.pb_cap = None
        self.is_pb_running = False
        self.is_pb_paused = False
        self.pb_selected_video_path = None
        self.pb_duration = 0.0
        self.pb_events_list = []

        # --- THIẾT LẬP STYLE CHO TREEVIEW VÀ WIDGETS ---
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background=self.BG_CARD, 
                        fieldbackground=self.BG_CARD, 
                        foreground=self.TXT_PRIMARY,
                        rowheight=32,
                        font=(self.FONT_NAME, 10),
                        borderwidth=0)
        style.configure("Treeview.Heading", 
                        background="#1e293b", 
                        foreground=self.TXT_PRIMARY,
                        relief="flat",
                        font=(self.FONT_NAME, 10, "bold"))
        style.map("Treeview", 
                  background=[("selected", self.ACCENT_BLUE)],
                  foreground=[("selected", "#ffffff")])
        
        style.configure("Horizontal.TScale",
                        background=self.BG_CARD,
                        troughcolor="#1e293b",
                        sliderthickness=12,
                        sliderlength=20)

        # --- GIAO DIỆN CHÍNH (SIDEBAR + CONTENT PANE) ---
        self.setup_main_layout()

    def create_standby_image(self, width=640, height=480, text="HỆ THỐNG TRONG TRẠNG THÁI CHỜ\n\nVui lòng nhấn nút Bắt đầu để vận hành"):
        img = Image.new("RGB", (width, height), color="#131b2e")
        draw = ImageDraw.Draw(img)
        
        # Vẽ viền và trang trí công nghệ cao
        pad = 20
        # Bốn góc bo viền
        draw.line([(pad, pad), (pad + 30, pad)], fill="#1e293b", width=2)
        draw.line([(pad, pad), (pad, pad + 30)], fill="#1e293b", width=2)
        draw.line([(width - pad, pad), (width - pad - 30, pad)], fill="#1e293b", width=2)
        draw.line([(width - pad, pad), (width - pad, pad + 30)], fill="#1e293b", width=2)
        draw.line([(pad, height - pad), (pad + 30, height - pad)], fill="#1e293b", width=2)
        draw.line([(pad, height - pad), (pad, height - pad - 30)], fill="#1e293b", width=2)
        draw.line([(width - pad, height - pad), (width - pad - 30, height - pad)], fill="#1e293b", width=2)
        draw.line([(width - pad, height - pad), (width - pad, height - pad - 30)], fill="#1e293b", width=2)
        
        # Vẽ các vòng tròn đồng tâm ở giữa đại diện cho camera/radar quét
        draw.ellipse([(width//2 - 60, height//2 - 80), (width//2 + 60, height//2 + 40)], outline="#1e293b", width=1)
        draw.ellipse([(width//2 - 40, height//2 - 60), (width//2 + 40, height//2 + 20)], outline="#1f2937", width=2)
        draw.ellipse([(width//2 - 20, height//2 - 40), (width//2 + 20, height//2)], outline=self.ACCENT_BLUE, width=2)
        
        font = None
        try:
            # Tìm font Segoe UI hoặc Arial trên Windows
            font_path = "C:\\Windows\\Fonts\\segoeui.ttf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 14)
        except Exception:
            pass
            
        lines = text.split("\n")
        y_text = height//2 + 60
        for line in lines:
            if font:
                bbox = draw.textbbox((0, 0), line, font=font)
                w_text = bbox[2] - bbox[0]
                h_text = bbox[3] - bbox[1]
                draw.text(((width - w_text)//2, y_text), line, font=font, fill=self.TXT_SECONDARY)
                y_text += h_text + 8
            else:
                draw.text((width//2 - 120, y_text), line, fill=self.TXT_SECONDARY)
                y_text += 16
                
        return ImageTk.PhotoImage(img)

    def create_sidebar_button(self, parent, text, icon, page_frame):
        # Frame bọc ngoài nút
        btn_frame = tk.Frame(parent, bg=self.BG_SIDEBAR, height=52)
        btn_frame.pack(fill=tk.X, pady=4, padx=10)
        btn_frame.pack_propagate(False)
        
        # Thanh chỉ thị đứng (Vertical Indicator)
        indicator = tk.Frame(btn_frame, bg=self.BG_SIDEBAR, width=4)
        indicator.pack(side=tk.LEFT, fill=tk.Y)
        
        # Nút bấm thực tế
        btn = tk.Button(btn_frame, text=f" {icon}   {text}", font=(self.FONT_NAME, 10, "bold"),
                        bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY, bd=0, activebackground=self.BG_SIDEBAR,
                        activeforeground=self.TXT_PRIMARY, cursor="hand2", anchor=tk.W, relief="flat")
        btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))
        
        btn.config(command=lambda: self.show_page(page_frame, btn))
        
        # Lưu vào dict để quản lý trạng thái
        self.nav_items[btn] = (indicator, btn_frame)
        
        btn.bind("<Enter>", lambda e: self.on_sidebar_hover(btn, True))
        btn.bind("<Leave>", lambda e: self.on_sidebar_hover(btn, False))
        
        return btn

    def on_sidebar_hover(self, btn, is_hover):
        indicator, btn_frame = self.nav_items[btn]
        # Chỉ hover khi nút bấm không được kích hoạt (indicator có màu trùng với nền sidebar)
        if indicator["bg"] == self.BG_SIDEBAR:
            if is_hover:
                btn.config(bg="#131b2e", fg=self.TXT_PRIMARY)
                btn_frame.config(bg="#131b2e")
            else:
                btn.config(bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY)
                btn_frame.config(bg=self.BG_SIDEBAR)

    def setup_main_layout(self):
        # Dictionary quản lý menu items
        self.nav_items = {}

        # 1. SIDEBAR PANEL (Bên trái)
        self.sidebar_frame = tk.Frame(self.root, bg=self.BG_SIDEBAR, width=250)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_frame.pack_propagate(False)

        # Tiêu đề Sidebar
        lbl_logo = tk.Label(self.sidebar_frame, text="🐾 CAT BEHAVIOR AI", font=(self.FONT_NAME, 16, "bold"),
                            bg=self.BG_SIDEBAR, fg=self.ACCENT_EMERALD)
        lbl_logo.pack(pady=35)

        # 2. CONTENT PANE (Bên phải)
        self.content_frame = tk.Frame(self.root, bg=self.BG_MAIN)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Các trang con
        self.camera_page = tk.Frame(self.content_frame, bg=self.BG_MAIN)
        self.video_page = tk.Frame(self.content_frame, bg=self.BG_MAIN)
        self.playback_page = tk.Frame(self.content_frame, bg=self.BG_MAIN)

        for frame in (self.camera_page, self.video_page, self.playback_page):
            frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Tạo nút điều hướng
        self.btn_nav_cam = self.create_sidebar_button(self.sidebar_frame, "GIÁM SÁT CAMERA", "🎥", self.camera_page)
        self.btn_nav_vid = self.create_sidebar_button(self.sidebar_frame, "PHÂN TÍCH VIDEO", "📁", self.video_page)
        self.btn_nav_pb = self.create_sidebar_button(self.sidebar_frame, "LỊCH SỬ & XEM LẠI", "📊", self.playback_page)

        # Ghi chú trạng thái ở dưới cùng sidebar
        lbl_info = tk.Label(self.sidebar_frame, text="Hệ thống AI v1.2.0\nNhóm Độc Quyền", font=(self.FONT_NAME, 9),
                            bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY)
        lbl_info.pack(side=tk.BOTTOM, pady=25)

        # Cài đặt UI cho các trang con
        self.setup_camera_ui()
        self.setup_video_ui()
        self.setup_playback_ui()

        # Mặc định mở trang camera đầu tiên
        self.show_page(self.camera_page, self.btn_nav_cam)

    def show_page(self, page, nav_button):
        self.stop_all_processes()
        
        # Cập nhật màu các nút menu để làm nổi bật trang hiện tại
        for btn, (indicator, btn_frame) in self.nav_items.items():
            if btn == nav_button:
                btn.config(bg="#1e293b", fg=self.TXT_PRIMARY)
                btn_frame.config(bg="#1e293b")
                indicator.config(bg=self.ACCENT_BLUE)
            else:
                btn.config(bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY)
                btn_frame.config(bg=self.BG_SIDEBAR)
                indicator.config(bg=self.BG_SIDEBAR)
                
        # Nâng trang lên trên cùng
        page.tkraise()
        
        # Nếu mở trang Playback, tải lại danh sách video từ DB
        if page == self.playback_page:
            self.load_all_playback_videos()

    def stop_all_processes(self):
        # 1. Lưu hành vi dở dang cuối cùng của video phân tích hoặc camera trực tiếp trước khi đóng
        if self.is_running and self.cap:
            if self.is_video_mode:
                if self.last_behavior_raw_db and self.current_video_id:
                    end_time = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                    avg_conf = sum(self.conf_list) / len(self.conf_list) if self.conf_list else 0
                    self.db.insert_behavior_event(
                        self.current_video_id, self.last_behavior_raw_db,
                        self.event_start_time, end_time, avg_conf
                    )
                    self.write_log(f"[DB] Ghi DB: {self.last_behavior_raw_db} ({self.event_start_time:.1f}s -> {end_time:.1f}s)", is_video=True)
            else:
                # Chế độ camera trực tiếp
                if self.cam_ai_active and self.last_cam_behavior_raw and self.current_session_id:
                    end_dt = datetime.now()
                    duration = (end_dt - self.cam_event_start_dt).total_seconds()
                    avg_conf = sum(self.cam_conf_list) / len(self.cam_conf_list) if self.cam_conf_list else 0
                    self.db.insert_camera_event(
                        self.current_session_id, self.last_cam_behavior_raw,
                        self.cam_event_start_dt, end_dt, duration, avg_conf
                    )
                    self.write_log(f"[DB] Ghi DB Camera: {self.last_cam_behavior_raw.replace('cat_eating', 'Mèo đang ăn').replace('cat_sitting', 'Mèo đang ngồi').replace('cat_sleeping', 'Mèo đang ngủ').replace('cat_standing', 'Mèo đang đứng')} ({duration:.1f}s)")
                
                if self.current_session_id:
                    self.db.end_camera_session(self.current_session_id)
                    self.write_log(f"[DB] Đã đóng phiên camera (ID: {self.current_session_id})")
                    self.current_session_id = None
                
                self.cam_ai_active = False

        # 2. Tắt camera/video phân tích
        self.is_running = False
        self.is_paused = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.last_behavior = None
        self.last_behavior_raw_db = None
        self.last_cam_behavior_raw = None
        self.cam_event_start_dt = None
        self.cam_conf_list = []
        
        # 3. Tắt trình phát video xem lại (Playback)
        self.is_pb_running = False
        self.is_pb_paused = False
        if self.pb_cap:
            self.pb_cap.release()
            self.pb_cap = None

        # Reset các khung hình hiển thị về ảnh chờ standby
        if hasattr(self, 'cam_video_frame'):
            self.cam_video_frame.config(image=self.standby_image)
        if hasattr(self, 'vid_display_frame'):
            self.vid_display_frame.config(image=self.standby_image)
        if hasattr(self, 'pb_video_label'):
            self.pb_video_label.config(image='')

    # =========================================================================
    # TAB 1: GIÁM SÁT CAMERA
    # =========================================================================
    def setup_camera_ui(self):
        # Khung Tiêu Đề
        header = tk.Label(self.camera_page, text="GIÁM SÁT REAL-TIME QUA CAMERA", 
                          font=(self.FONT_NAME, 20, "bold"), bg=self.BG_MAIN, fg=self.TXT_PRIMARY)
        header.pack(pady=20, anchor=tk.W, padx=30)

        main_content = tk.Frame(self.camera_page, bg=self.BG_MAIN)
        main_content.pack(fill=tk.BOTH, expand=True, padx=30)

        # Panel trái: Video hiển thị (Card container)
        left_panel = tk.Frame(main_content, bg=self.BG_CARD, width=640, height=480, 
                               highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        left_panel.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 20))
        left_panel.pack_propagate(False)

        self.cam_video_frame = tk.Label(left_panel, bg="#0b0f19", image=self.standby_image)
        self.cam_video_frame.pack(expand=True, fill=tk.BOTH)

        # Panel phải: Live Dashboard & Logs
        right_panel = tk.Frame(main_content, bg=self.BG_MAIN)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=(0, 20))

        # --- CARD 1: LIVE STATUS DASHBOARD ---
        self.cam_dash_card = tk.Frame(right_panel, bg=self.BG_CARD, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        self.cam_dash_card.pack(fill=tk.X, pady=(0, 15))
        
        # Tiêu đề Card
        tk.Label(self.cam_dash_card, text="BẢNG TRẠNG THÁI AI REAL-TIME", font=(self.FONT_NAME, 10, "bold"), 
                 bg=self.BG_CARD, fg=self.ACCENT_BLUE).pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        # Grid thông tin bên trong Card
        info_grid = tk.Frame(self.cam_dash_card, bg=self.BG_CARD)
        info_grid.pack(fill=tk.X, padx=15, pady=(5, 12))
        info_grid.columnconfigure(1, weight=1)
        
        # 1. Trạng thái hệ thống
        tk.Label(info_grid, text="Trạng thái hệ thống:", font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).grid(row=0, column=0, sticky=tk.W, pady=4)
        self.lbl_cam_status = tk.Label(info_grid, text="● NGOẠI TUYẾN", font=(self.FONT_NAME, 10, "bold"), bg=self.BG_CARD, fg=self.TXT_SECONDARY)
        self.lbl_cam_status.grid(row=0, column=1, sticky=tk.W, padx=10, pady=4)
        
        # 2. Hành vi hiện tại của mèo
        tk.Label(info_grid, text="Hành vi hiện tại:", font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).grid(row=1, column=0, sticky=tk.W, pady=4)
        
        # Thẻ badge chứa hành vi
        self.badge_cam_behavior = tk.Frame(info_grid, bg="#1e293b", padx=8, pady=4)
        self.badge_cam_behavior.grid(row=1, column=1, sticky=tk.W, padx=10, pady=4)
        self.lbl_cam_behavior = tk.Label(self.badge_cam_behavior, text="CHƯA PHÁT HIỆN", font=(self.FONT_NAME, 10, "bold"), bg="#1e293b", fg=self.TXT_SECONDARY)
        self.lbl_cam_behavior.pack()
        
        # 3. Độ tin cậy (Confidence Score)
        tk.Label(info_grid, text="Độ tin cậy:", font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).grid(row=2, column=0, sticky=tk.W, pady=4)
        
        conf_container = tk.Frame(info_grid, bg=self.BG_CARD)
        conf_container.grid(row=2, column=1, sticky=tk.W, padx=10, pady=4)
        
        self.progress_cam_conf = ttk.Progressbar(conf_container, orient=tk.HORIZONTAL, length=150, mode='determinate')
        self.progress_cam_conf.pack(side=tk.LEFT)
        
        self.lbl_cam_conf_val = tk.Label(conf_container, text="0%", font=(self.FONT_NAME, 9, "bold"), bg=self.BG_CARD, fg=self.TXT_PRIMARY)
        self.lbl_cam_conf_val.pack(side=tk.LEFT, padx=10)

        # --- CARD 2: LOG BOX & CONTROLS ---
        log_container = tk.Frame(right_panel, bg=self.BG_CARD, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(log_container, text="NHẬT KÝ HÀNH VI CAMERA", font=(self.FONT_NAME, 10, "bold"), bg=self.BG_CARD, fg=self.ACCENT_EMERALD).pack(anchor=tk.W, padx=15, pady=(10, 5))

        # Log box dạng Slate Card
        self.cam_log_box = scrolledtext.ScrolledText(log_container, font=(self.FONT_NAME, 10), bg="#0b0f19", fg=self.TXT_PRIMARY, bd=0, insertbackground="white")
        self.cam_log_box.pack(pady=5, padx=15, fill=tk.BOTH, expand=True)
        
        # Cấu hình màu cho log tags
        self.cam_log_box.tag_config("time", foreground="#64748b", font=(self.FONT_NAME, 9))
        self.cam_log_box.tag_config("detect", foreground="#06b6d4", font=(self.FONT_NAME, 10, "bold"))
        self.cam_log_box.tag_config("db", foreground="#c084fc", font=(self.FONT_NAME, 10))
        self.cam_log_box.tag_config("error", foreground="#f87171", font=(self.FONT_NAME, 10, "bold"))
        self.cam_log_box.tag_config("system", foreground="#94a3b8", font=(self.FONT_NAME, 10))
        self.cam_log_box.config(state=tk.DISABLED)

        # Khung chứa nút điều khiển bên dưới
        btn_panel = tk.Frame(log_container, bg=self.BG_CARD)
        btn_panel.pack(pady=15, padx=15, fill=tk.X)

        self.btn_cam_start = tk.Button(btn_panel, text="▶ MỞ CAMERA", font=(self.FONT_NAME, 10, "bold"), 
                                       bg=self.ACCENT_EMERALD, fg="white", bd=0, height=2, width=18, cursor="hand2",
                                       activebackground=self.ACCENT_EMERALD_HOVER, activeforeground="white",
                                       command=self.start_camera)
        self.btn_cam_start.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_cam_stop = tk.Button(btn_panel, text="⏹ DỪNG CAMERA", font=(self.FONT_NAME, 10, "bold"), 
                                      bg=self.ACCENT_RED, fg="white", bd=0, height=2, width=18, cursor="hand2",
                                      activebackground=self.ACCENT_RED_HOVER, activeforeground="white",
                                      command=self.stop_camera)
        self.btn_cam_stop.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_cam_stop.config(state=tk.DISABLED)

        # Nút bật/tắt nhận diện AI
        self.btn_cam_toggle_ai = tk.Button(btn_panel, text="🤖 BẬT AI NHẬN DẠNG", font=(self.FONT_NAME, 10, "bold"), 
                                           bg=self.ACCENT_BLUE, fg="white", bd=0, height=2, width=20, cursor="hand2",
                                           activebackground=self.ACCENT_BLUE_HOVER, activeforeground="white")
        self.btn_cam_toggle_ai.pack(side=tk.LEFT)
        self.btn_cam_toggle_ai.config(state=tk.DISABLED, command=self.toggle_cam_ai)
        
        # Bắt hiệu ứng hover cho nút bấm điều khiển
        self.btn_cam_start.bind("<Enter>", lambda e: self.btn_cam_start.config(bg=self.ACCENT_EMERALD_HOVER) if self.btn_cam_start["state"] != tk.DISABLED else None)
        self.btn_cam_start.bind("<Leave>", lambda e: self.btn_cam_start.config(bg=self.ACCENT_EMERALD) if self.btn_cam_start["state"] != tk.DISABLED else None)
        self.btn_cam_stop.bind("<Enter>", lambda e: self.btn_cam_stop.config(bg=self.ACCENT_RED_HOVER) if self.btn_cam_stop["state"] != tk.DISABLED else None)
        self.btn_cam_stop.bind("<Leave>", lambda e: self.btn_cam_stop.config(bg=self.ACCENT_RED) if self.btn_cam_stop["state"] != tk.DISABLED else None)
        self.btn_cam_toggle_ai.bind("<Enter>", lambda e: self.btn_cam_toggle_ai.config(bg=self.btn_cam_toggle_ai_hover_color()) if self.btn_cam_toggle_ai["state"] != tk.DISABLED else None)
        self.btn_cam_toggle_ai.bind("<Leave>", lambda e: self.btn_cam_toggle_ai.config(bg=self.btn_cam_toggle_ai_normal_color()) if self.btn_cam_toggle_ai["state"] != tk.DISABLED else None)

    def write_log(self, message, is_video=False):
        current_time = datetime.now().strftime("%H:%M:%S")
        log_box = self.vid_log_box if is_video else self.cam_log_box
        
        log_box.config(state=tk.NORMAL)
        log_box.insert(tk.END, f"[{current_time}] ", "time")
        
        # Phân loại message để gán tag màu
        if "Phát hiện:" in message:
            log_box.insert(tk.END, f"{message}\n", "detect")
        elif "[DB]" in message or "Ghi DB:" in message or "đã có trong DB" in message or "Đăng ký video mới" in message or "Đã đăng ký video" in message:
            log_box.insert(tk.END, f"{message}\n", "db")
        elif "Lỗi" in message or "Cảnh báo" in message or "Không tìm thấy" in message or "thất bại" in message:
            log_box.insert(tk.END, f"{message}\n", "error")
        else:
            log_box.insert(tk.END, f"{message}\n", "system")
            
        log_box.config(state=tk.DISABLED)
        log_box.see(tk.END)

    def update_live_badge(self, is_video, behavior_raw, conf):
        lbl_behavior = self.lbl_vid_behavior if is_video else self.lbl_cam_behavior
        badge_behavior = self.badge_vid_behavior if is_video else self.badge_cam_behavior
        progress_conf = self.progress_vid_conf if is_video else self.progress_cam_conf
        lbl_conf_val = self.lbl_vid_conf_val if is_video else self.lbl_cam_conf_val
        
        if behavior_raw and conf >= 0.75:
            # Map raw name to Vietnamese label
            vi_label = behavior_raw.replace("cat_eating", "MÈO ĐANG ĂN")\
                                   .replace("cat_sitting", "MÈO ĐANG NGỒI")\
                                   .replace("cat_sleeping", "MÈO ĐANG NGỦ")\
                                   .replace("cat_standing", "MÈO ĐANG ĐỨNG")
            
            # Map color based on behavior
            bg_color = "#1e293b"
            if "eating" in behavior_raw:
                bg_color = self.ACCENT_EMERALD
            elif "sitting" in behavior_raw:
                bg_color = self.ACCENT_YELLOW
            elif "sleeping" in behavior_raw:
                bg_color = self.ACCENT_BLUE
            elif "standing" in behavior_raw:
                bg_color = "#f97316" # Orange
                
            badge_behavior.config(bg=bg_color)
            lbl_behavior.config(text=vi_label, fg="white", bg=bg_color)
            
            # Update progress bar and text value
            val = int(conf * 100)
            progress_conf['value'] = val
            lbl_conf_val.config(text=f"{val}%")
        else:
            badge_behavior.config(bg="#1e293b")
            lbl_behavior.config(text="CHƯA PHÁT HIỆN", fg=self.TXT_SECONDARY, bg="#1e293b")
            progress_conf['value'] = 0
            lbl_conf_val.config(text="0%")

    def start_camera(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Lỗi", "Không tìm thấy Camera!")
                return
            self.is_running = True
            self.is_video_mode = False
            self.is_paused = False
            self.btn_cam_start.config(state=tk.DISABLED)
            self.btn_cam_stop.config(state=tk.NORMAL)
            self.btn_cam_toggle_ai.config(state=tk.NORMAL, text="🤖 BẬT AI NHẬN DẠNG", bg=self.ACCENT_BLUE)
            self.lbl_cam_status.config(text="● ĐANG HIỂN THỊ CAMERA THƯỜNG", fg=self.ACCENT_BLUE)
            
            # Khởi tạo camera session trong DB
            session_name = f"Camera Live {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            self.current_session_id = self.db.insert_camera_session(session_name)
            self.last_cam_behavior_raw = None
            self.cam_event_start_dt = None
            self.cam_conf_list = []
            self.cam_ai_active = False
            
            self.write_log("Hệ thống: Bắt đầu giám sát Camera...")
            if self.current_session_id:
                self.write_log(f"[DB] Đã khởi tạo phiên camera mới (ID: {self.current_session_id})")
                
            self.update_frame()

    def stop_camera(self):
        self.stop_all_processes()
        self.btn_cam_start.config(state=tk.NORMAL)
        self.btn_cam_stop.config(state=tk.DISABLED)
        self.btn_cam_toggle_ai.config(state=tk.DISABLED, text="🤖 BẬT AI NHẬN DẠNG", bg=self.ACCENT_BLUE)
        self.lbl_cam_status.config(text="● NGOẠI TUYẾN", fg=self.TXT_SECONDARY)
        self.update_live_badge(is_video=False, behavior_raw=None, conf=0.0)
        self.write_log("Hệ thống: Đã dừng camera.")

    # =========================================================================
    # TAB 2: PHÂN TÍCH VIDEO FILE (IMPORT)
    # =========================================================================
    def setup_video_ui(self):
        header = tk.Label(self.video_page, text="PHÂN TÍCH HÀNH VI QUA VIDEO ĐÃ LƯU", 
                          font=(self.FONT_NAME, 20, "bold"), bg=self.BG_MAIN, fg=self.TXT_PRIMARY)
        header.pack(pady=20, anchor=tk.W, padx=30)

        main_content = tk.Frame(self.video_page, bg=self.BG_MAIN)
        main_content.pack(fill=tk.BOTH, expand=True, padx=30)

        # Panel trái: Video hiển thị (Card container)
        left_panel = tk.Frame(main_content, bg=self.BG_CARD, width=640, height=480, 
                               highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        left_panel.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 20))
        left_panel.pack_propagate(False)

        self.vid_display_frame = tk.Label(left_panel, bg="#0b0f19", image=self.standby_image)
        self.vid_display_frame.pack(expand=True, fill=tk.BOTH)

        # Panel phải: Kết quả phân tích (Lưu DB)
        right_panel = tk.Frame(main_content, bg=self.BG_MAIN)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=(0, 20))

        # --- CARD 1: LIVE STATUS DASHBOARD (VIDEO) ---
        self.vid_dash_card = tk.Frame(right_panel, bg=self.BG_CARD, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        self.vid_dash_card.pack(fill=tk.X, pady=(0, 15))
        
        # Tiêu đề Card
        tk.Label(self.vid_dash_card, text="KẾT QUẢ AI DỰ BÁO TRỰC TIẾP", font=(self.FONT_NAME, 10, "bold"), 
                 bg=self.BG_CARD, fg=self.ACCENT_BLUE).pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        # Grid thông tin bên trong Card
        info_grid = tk.Frame(self.vid_dash_card, bg=self.BG_CARD)
        info_grid.pack(fill=tk.X, padx=15, pady=(5, 12))
        info_grid.columnconfigure(1, weight=1)
        
        # 1. Trạng thái phân tích
        tk.Label(info_grid, text="Trạng thái phân tích:", font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).grid(row=0, column=0, sticky=tk.W, pady=4)
        self.lbl_vid_status = tk.Label(info_grid, text="● CHỜ PHÂN TÍCH / CHƯA IMPORT", font=(self.FONT_NAME, 10, "bold"), bg=self.BG_CARD, fg=self.TXT_SECONDARY)
        self.lbl_vid_status.grid(row=0, column=1, sticky=tk.W, padx=10, pady=4)
        
        # 2. Hành vi mèo dự báo
        tk.Label(info_grid, text="Hành vi mèo dự báo:", font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).grid(row=1, column=0, sticky=tk.W, pady=4)
        
        # Thẻ badge chứa hành vi
        self.badge_vid_behavior = tk.Frame(info_grid, bg="#1e293b", padx=8, pady=4)
        self.badge_vid_behavior.grid(row=1, column=1, sticky=tk.W, padx=10, pady=4)
        self.lbl_vid_behavior = tk.Label(self.badge_vid_behavior, text="CHƯA PHÁT HIỆN", font=(self.FONT_NAME, 10, "bold"), bg="#1e293b", fg=self.TXT_SECONDARY)
        self.lbl_vid_behavior.pack()
        
        # 3. Độ tin cậy (Confidence Score)
        tk.Label(info_grid, text="Độ tin cậy:", font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).grid(row=2, column=0, sticky=tk.W, pady=4)
        
        conf_container = tk.Frame(info_grid, bg=self.BG_CARD)
        conf_container.grid(row=2, column=1, sticky=tk.W, padx=10, pady=4)
        
        self.progress_vid_conf = ttk.Progressbar(conf_container, orient=tk.HORIZONTAL, length=150, mode='determinate')
        self.progress_vid_conf.pack(side=tk.LEFT)
        
        self.lbl_vid_conf_val = tk.Label(conf_container, text="0%", font=(self.FONT_NAME, 9, "bold"), bg=self.BG_CARD, fg=self.TXT_PRIMARY)
        self.lbl_vid_conf_val.pack(side=tk.LEFT, padx=10)

        # --- CARD 2: LOG BOX & CONTROLS ---
        log_container = tk.Frame(right_panel, bg=self.BG_CARD, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        log_container.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_container, text="KẾT QUẢ PHÂN TÍCH VIDEO (LƯU DB)", font=(self.FONT_NAME, 10, "bold"), bg=self.BG_CARD, fg=self.ACCENT_EMERALD).pack(anchor=tk.W, padx=15, pady=(10, 5))

        self.vid_log_box = scrolledtext.ScrolledText(log_container, font=(self.FONT_NAME, 10), bg="#0b0f19", fg=self.TXT_PRIMARY, bd=0, insertbackground="white")
        self.vid_log_box.pack(pady=5, padx=15, fill=tk.BOTH, expand=True)
        
        self.vid_log_box.tag_config("time", foreground="#64748b", font=(self.FONT_NAME, 9))
        self.vid_log_box.tag_config("detect", foreground="#06b6d4", font=(self.FONT_NAME, 10, "bold"))
        self.vid_log_box.tag_config("db", foreground="#c084fc", font=(self.FONT_NAME, 10))
        self.vid_log_box.tag_config("error", foreground="#f87171", font=(self.FONT_NAME, 10, "bold"))
        self.vid_log_box.tag_config("system", foreground="#94a3b8", font=(self.FONT_NAME, 10))
        self.vid_log_box.config(state=tk.DISABLED)

        # Nút điều khiển
        btn_panel = tk.Frame(log_container, bg=self.BG_CARD)
        btn_panel.pack(pady=15, padx=15, fill=tk.X)

        self.btn_vid_import = tk.Button(btn_panel, text="📁 CHỌN VIDEO", font=(self.FONT_NAME, 9, "bold"), 
                  bg=self.ACCENT_BLUE, fg="white", bd=0, height=2, width=15, cursor="hand2",
                  activebackground=self.ACCENT_BLUE_HOVER, activeforeground="white",
                  command=self.import_video)
        self.btn_vid_import.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_vid_play = tk.Button(btn_panel, text="▶ PHÂN TÍCH", font=(self.FONT_NAME, 9, "bold"), 
                                      bg=self.ACCENT_EMERALD, fg="white", bd=0, height=2, width=15, cursor="hand2",
                                      activebackground=self.ACCENT_EMERALD_HOVER, activeforeground="white",
                                      command=self.play_video)
        self.btn_vid_play.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_vid_play.config(state=tk.DISABLED)

        self.btn_vid_pause = tk.Button(btn_panel, text="⏸ TẠM DỪNG", font=(self.FONT_NAME, 9, "bold"), 
                                       bg=self.ACCENT_YELLOW, fg="white", bd=0, height=2, width=15, cursor="hand2",
                                       activebackground=self.ACCENT_YELLOW_HOVER, activeforeground="white",
                                       command=self.toggle_pause)
        self.btn_vid_pause.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_vid_pause.config(state=tk.DISABLED)

        self.btn_vid_stop = tk.Button(btn_panel, text="⏹ DỪNG LẠI", font=(self.FONT_NAME, 9, "bold"), 
                                      bg=self.ACCENT_RED, fg="white", bd=0, height=2, width=15, cursor="hand2",
                                      activebackground=self.ACCENT_RED_HOVER, activeforeground="white",
                                      command=self.stop_video)
        self.btn_vid_stop.pack(side=tk.LEFT)
        self.btn_vid_stop.config(state=tk.DISABLED)
        
        # Bắt hiệu ứng hover cho nút bấm điều khiển video
        self.btn_vid_import.bind("<Enter>", lambda e: self.btn_vid_import.config(bg=self.ACCENT_BLUE_HOVER) if self.btn_vid_import["state"] != tk.DISABLED else None)
        self.btn_vid_import.bind("<Leave>", lambda e: self.btn_vid_import.config(bg=self.ACCENT_BLUE) if self.btn_vid_import["state"] != tk.DISABLED else None)
        self.btn_vid_play.bind("<Enter>", lambda e: self.btn_vid_play.config(bg=self.ACCENT_EMERALD_HOVER) if self.btn_vid_play["state"] != tk.DISABLED else None)
        self.btn_vid_play.bind("<Leave>", lambda e: self.btn_vid_play.config(bg=self.ACCENT_EMERALD) if self.btn_vid_play["state"] != tk.DISABLED else None)
        self.btn_vid_pause.bind("<Enter>", lambda e: self.btn_vid_pause.config(bg=self.ACCENT_YELLOW_HOVER) if self.btn_vid_pause["state"] != tk.DISABLED else None)
        self.btn_vid_pause.bind("<Leave>", lambda e: self.btn_vid_pause.config(bg=self.ACCENT_YELLOW) if self.btn_vid_pause["state"] != tk.DISABLED else None)
        self.btn_vid_stop.bind("<Enter>", lambda e: self.btn_vid_stop.config(bg=self.ACCENT_RED_HOVER) if self.btn_vid_stop["state"] != tk.DISABLED else None)
        self.btn_vid_stop.bind("<Leave>", lambda e: self.btn_vid_stop.config(bg=self.ACCENT_RED) if self.btn_vid_stop["state"] != tk.DISABLED else None)

    def get_video_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_safe_video_path(self, file_path):
        # Kiểm tra xem đường dẫn có chứa ký tự non-ASCII không
        try:
            file_path.encode('ascii')
            return file_path
        except UnicodeEncodeError:
            # Nếu chứa ký tự non-ASCII, copy sang file tạm ở thư mục chứa app (đảm bảo là đường dẫn ASCII)
            app_dir = os.path.dirname(os.path.abspath(__file__))
            ext = os.path.splitext(file_path)[1]
            temp_path = os.path.join(app_dir, f"temp_analysis{ext}")
            
            # Xóa file tạm cũ nếu có
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                    
            import shutil
            try:
                shutil.copy2(file_path, temp_path)
                return temp_path
            except Exception as e:
                print(f"Error copying to temp path: {e}")
                return file_path

    def import_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        if file_path:
            self.stop_all_processes()
            self.video_path = file_path
            
            # Đảm bảo video_path là ASCII để OpenCV đọc được trên Windows
            self.video_path_safe = self.get_safe_video_path(file_path)
            
            # --- Xử lý Database ---
            v_hash = self.get_video_hash(file_path)
            video_rec = self.db.get_video_by_hash(v_hash)
            if video_rec:
                self.current_video_id = video_rec['id']
                self.write_log(f"Video đã có trong DB (ID: {self.current_video_id})", is_video=True)
            else:
                cap = cv2.VideoCapture(self.video_path_safe)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                
                self.current_video_id = self.db.insert_video(
                    os.path.basename(file_path), file_path, v_hash, duration
                )
                self.write_log(f"Đăng ký video mới thành công (ID: {self.current_video_id})", is_video=True)

            self.btn_vid_play.config(state=tk.NORMAL)
            self.btn_vid_pause.config(state=tk.DISABLED)
            self.btn_vid_stop.config(state=tk.DISABLED)
            self.lbl_vid_status.config(text="● ĐÃ IMPORT / SẴN SÀNG PHÂN TÍCH", fg=self.ACCENT_BLUE)
            self.write_log(f"Sẵn sàng phân tích: {os.path.basename(file_path)}", is_video=True)

    def play_video(self):
        if hasattr(self, 'video_path'):
            if not self.is_running:
                self.cap = cv2.VideoCapture(self.video_path_safe)
                if not self.cap.isOpened():
                    messagebox.showerror("Lỗi", "Không thể mở file video!")
                    return
                self.is_running = True
                self.is_video_mode = True
                self.is_paused = False
                
                # Đọc FPS thực tế của video để đồng bộ thời gian chạy
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.fps = fps if fps > 0 else 30.0
                self.analysis_delay = int(1000 / self.fps)
                
                # Tính tổng thời lượng để làm điểm mốc cuối cùng chính xác
                frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.video_duration = frame_count / self.fps if self.fps > 0 else 0.0
                
                # Khởi tạo lại trạng thái hành vi lưu DB
                self.last_behavior = None
                self.last_behavior_raw_db = None
                self.event_start_time = 0
                self.conf_list = []
                
                self.btn_vid_play.config(state=tk.DISABLED)
                self.btn_vid_pause.config(state=tk.NORMAL, text="⏸ TẠM DỪNG")
                self.btn_vid_stop.config(state=tk.NORMAL)
                self.lbl_vid_status.config(text="● ĐANG TIẾN HÀNH PHÂN TÍCH...", fg=self.ACCENT_EMERALD)
                self.write_log("Đang tiến hành phân tích các khung hình video...", is_video=True)
                self.update_frame()

    def toggle_pause(self):
        if self.is_running:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.btn_vid_pause.config(text="▶ TIẾP TỤC", bg=self.ACCENT_EMERALD)
                self.lbl_vid_status.config(text="● TẠM DỪNG PHÂN TÍCH", fg=self.ACCENT_YELLOW)
                self.write_log("Đang tạm dừng phân tích video.", is_video=True)
            else:
                self.btn_vid_pause.config(text="⏸ TẠM DỪNG", bg=self.ACCENT_YELLOW)
                self.lbl_vid_status.config(text="● ĐANG TIẾN HÀNH PHÂN TÍCH...", fg=self.ACCENT_EMERALD)
                self.write_log("Tiếp tục phân tích.", is_video=True)
                self.update_frame()

    def stop_video(self):
        self.stop_all_processes()
        self.btn_vid_play.config(state=tk.NORMAL)
        self.btn_vid_pause.config(state=tk.DISABLED, text="⏸ TẠM DỪNG", bg=self.ACCENT_YELLOW)
        self.btn_vid_stop.config(state=tk.DISABLED)
        self.lbl_vid_status.config(text="● ĐÃ DỪNG PHÂN TÍCH", fg=self.TXT_SECONDARY)
        self.update_live_badge(is_video=True, behavior_raw=None, conf=0.0)
        self.write_log("Đã dừng hoạt động phân tích.", is_video=True)

    # =========================================================================
    # TAB 3: LỊCH SỬ & XEM LẠI VIDEO ĐÃ PHÂN TÍCH (NEW)
    # =========================================================================
    def setup_playback_ui(self):
        self.pb_mode = "video" # Mặc định xem lịch sử video

        header = tk.Label(self.playback_page, text="LỊCH SỬ PHÂN TÍCH & XEM LẠI", 
                          font=(self.FONT_NAME, 20, "bold"), bg=self.BG_MAIN, fg=self.TXT_PRIMARY)
        header.pack(pady=20, anchor=tk.W, padx=30)

        main_content = tk.Frame(self.playback_page, bg=self.BG_MAIN)
        main_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))

        # --- PANEL TRÁI: DANH SÁCH LỊCH SỬ ---
        left_panel = tk.Frame(main_content, bg=self.BG_MAIN, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_panel.pack_propagate(False)

        # Nút chuyển đổi chế độ xem Lịch sử (Video vs Camera)
        mode_frame = tk.Frame(left_panel, bg=self.BG_MAIN)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_pb_mode_vid = tk.Button(mode_frame, text="PHÂN TÍCH VIDEO", font=(self.FONT_NAME, 9, "bold"),
                                         bg=self.ACCENT_BLUE, fg="white", bd=0, height=2, cursor="hand2",
                                         activebackground=self.ACCENT_BLUE_HOVER, activeforeground="white")
        self.btn_pb_mode_vid.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        
        self.btn_pb_mode_cam = tk.Button(mode_frame, text="CAMERA LIVE", font=(self.FONT_NAME, 9, "bold"),
                                         bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY, bd=0, height=2, cursor="hand2",
                                         activebackground="#1e293b", activeforeground=self.TXT_PRIMARY)
        self.btn_pb_mode_cam.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        
        self.btn_pb_mode_vid.config(command=lambda: self.switch_playback_mode("video"))
        self.btn_pb_mode_cam.config(command=lambda: self.switch_playback_mode("camera"))

        tk.Label(left_panel, text="DANH SÁCH BẢN GHI", font=(self.FONT_NAME, 11, "bold"), bg=self.BG_MAIN, fg=self.TXT_PRIMARY).pack(anchor=tk.W, pady=(0, 5))

        # Bọc Treeview trong một Card Frame
        tree_card = tk.Frame(left_panel, bg=self.BG_CARD, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        tree_card.pack(fill=tk.BOTH, expand=True)

        # Bảng hiển thị danh sách video/camera
        cols = ("ID", "Tên File", "Đường Dẫn", "Thời Gian", "Thời Lượng")
        self.tree_videos = ttk.Treeview(tree_card, columns=cols, show="headings")
        self.tree_videos.heading("ID", text="ID")
        self.tree_videos.heading("Tên File", text="Tên File Video")
        self.tree_videos.heading("Đường Dẫn", text="Đường Dẫn")
        self.tree_videos.heading("Thời Gian", text="Thời Gian Phân Tích")
        self.tree_videos.heading("Thời Lượng", text="Độ Dài")

        # Điều chỉnh kích thước cột (ngăn co rút các cột cố định)
        self.tree_videos.column("ID", width=35, minwidth=30, stretch=tk.NO, anchor=tk.CENTER)
        self.tree_videos.column("Tên File", width=140, minwidth=100, stretch=tk.YES)
        self.tree_videos.column("Đường Dẫn", width=0, stretch=tk.NO)  # Ẩn cột đường dẫn (status cho camera)
        self.tree_videos.column("Thời Gian", width=110, minwidth=90, stretch=tk.NO)
        self.tree_videos.column("Thời Lượng", width=55, minwidth=50, stretch=tk.NO, anchor=tk.CENTER)

        # Thanh cuộn dọc cho bảng video
        sb_video = ttk.Scrollbar(tree_card, orient=tk.VERTICAL, command=self.tree_videos.yview)
        self.tree_videos.configure(yscrollcommand=sb_video.set)
        
        self.tree_videos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_video.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_videos.bind("<<TreeviewSelect>>", self.on_video_select)

        # --- PANEL PHẢI: VIDEO PLAYER VÀ BẢNG SỰ KIỆN ---
        right_panel = tk.Frame(main_content, bg=self.BG_MAIN)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Bố cục chia hai nửa trong panel phải
        right_top = tk.Frame(right_panel, bg=self.BG_MAIN)
        right_top.pack(fill=tk.BOTH, expand=True)

        # Nửa trên bên phải: Bảng chi tiết sự kiện (Độ rộng 350px đối xứng hoàn hảo với bảng bên trái) - Đóng gói trước để giữ vị trí khi responsive
        events_card = tk.Frame(right_top, bg=self.BG_CARD, width=350, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        events_card.pack(side=tk.RIGHT, fill=tk.Y)
        events_card.pack_propagate(False)

        # Nửa trên bên trái: Trình phát video hoặc Bảng thống kê (Player Card)
        player_frame = tk.Frame(right_top, bg=self.BG_CARD, width=480, height=360, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        player_frame.pack(side=tk.LEFT, padx=(0, 15), fill=tk.BOTH, expand=True)
        player_frame.pack_propagate(False)

        # 1. Khung hiển thị video xem lại
        self.pb_video_label = tk.Label(player_frame, bg="#0b0f19", image=self.standby_image)
        self.pb_video_label.pack(expand=True, fill=tk.BOTH)

        # 2. Khung thống kê số liệu Camera (Sẽ được pack/unpack động)
        self.stats_frame = tk.Frame(player_frame, bg=self.BG_CARD)
        self.setup_stats_ui()

        tk.Label(events_card, text="CHI TIẾT SỰ KIỆN AI", font=(self.FONT_NAME, 10, "bold"), bg=events_card["bg"], fg=self.ACCENT_BLUE).pack(anchor=tk.W, padx=15, pady=(10, 5))

        event_cols = ("Hành Vi", "Bắt Đầu", "Kết Thúc", "Độ Tin Cậy")
        self.tree_events = ttk.Treeview(events_card, columns=event_cols, show="headings")
        self.tree_events.heading("Hành Vi", text="Hành Vi")
        self.tree_events.heading("Bắt Đầu", text="Bắt Đầu")
        self.tree_events.heading("Kết Thúc", text="Kết Thúc")
        self.tree_events.heading("Độ Tin Cậy", text="Độ Tin Cậy")

        # Cấu hình không cho co giãn các cột số liệu, chỉ cột Hành Vi co giãn tự do
        self.tree_events.column("Hành Vi", width=105, minwidth=90, stretch=tk.YES)
        self.tree_events.column("Bắt Đầu", width=60, minwidth=55, stretch=tk.NO, anchor=tk.CENTER)
        self.tree_events.column("Kết Thúc", width=60, minwidth=55, stretch=tk.NO, anchor=tk.CENTER)
        self.tree_events.column("Độ Tin Cậy", width=75, minwidth=70, stretch=tk.NO, anchor=tk.CENTER)

        # Thanh cuộn dọc cho bảng sự kiện
        sb_event = ttk.Scrollbar(events_card, orient=tk.VERTICAL, command=self.tree_events.yview)
        self.tree_events.configure(yscrollcommand=sb_event.set)
        
        self.tree_events.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        sb_event.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 15), padx=(0, 15))
        self.tree_events.bind("<Double-1>", self.on_event_double_click)

        # --- NỬA DƯỚI: THANH ĐIỀU KHIỂN VIDEO PLAYER ---
        player_controls = tk.Frame(right_panel, bg=self.BG_CARD, height=85, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        player_controls.pack(fill=tk.X, pady=(15, 0))
        player_controls.pack_propagate(False)
        
        # 1. Slider Dòng thời gian
        self.slider_pb = ttk.Scale(player_controls, from_=0, to=100, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_pb.pack(fill=tk.X, padx=15, pady=(8, 4))
        self.slider_pb.bind("<ButtonRelease-1>", self.on_slider_release)
        self.slider_pb.bind("<B1-Motion>", self.on_slider_drag)
        self.is_pb_seeking = False

        # 2. Hàng nút điều khiển
        control_row = tk.Frame(player_controls, bg=self.BG_CARD)
        control_row.pack(fill=tk.X, padx=15, pady=(0, 5))

        self.btn_play_pb = tk.Button(control_row, text="▶ PHÁT", font=(self.FONT_NAME, 9, "bold"),
                                     bg=self.ACCENT_EMERALD, fg="white", bd=0, height=2, width=12, cursor="hand2",
                                     activebackground=self.ACCENT_EMERALD_HOVER, activeforeground="white")
        self.btn_play_pb.pack(side=tk.LEFT)
        self.btn_play_pb.config(state=tk.DISABLED, command=self.toggle_pb_pause)

        self.btn_stop_pb = tk.Button(control_row, text="⏹ DỪNG", font=(self.FONT_NAME, 9, "bold"),
                                     bg=self.ACCENT_RED, fg="white", bd=0, height=2, width=12, cursor="hand2",
                                     activebackground=self.ACCENT_RED_HOVER, activeforeground="white")
        self.btn_stop_pb.pack(side=tk.LEFT, padx=10)
        self.btn_stop_pb.config(state=tk.DISABLED, command=self.stop_pb_video)
        
        # Bắt hiệu ứng hover cho các nút phát xem lại
        self.btn_play_pb.bind("<Enter>", lambda e: self.btn_play_pb.config(bg=self.ACCENT_EMERALD_HOVER) if self.btn_play_pb["state"] != tk.DISABLED else None)
        self.btn_play_pb.bind("<Leave>", lambda e: self.btn_play_pb.config(bg=self.ACCENT_EMERALD) if self.btn_play_pb["state"] != tk.DISABLED else None)
        self.btn_stop_pb.bind("<Enter>", lambda e: self.btn_stop_pb.config(bg=self.ACCENT_RED_HOVER) if self.btn_stop_pb["state"] != tk.DISABLED else None)
        self.btn_stop_pb.bind("<Leave>", lambda e: self.btn_stop_pb.config(bg=self.ACCENT_RED) if self.btn_stop_pb["state"] != tk.DISABLED else None)

        # Nhãn hiển thị thời gian
        self.lbl_time_pb = tk.Label(control_row, text="0.0s / 0.0s", font=("Consolas", 10, "bold"),
                                    bg=self.BG_CARD, fg=self.TXT_PRIMARY)
        self.lbl_time_pb.pack(side=tk.RIGHT, pady=5)

        # Ghi chú hướng dẫn ở góc dưới
        self.lbl_pb_hint = tk.Label(right_panel, text="* Mẹo: Nhấp đúp chuột vào một hành vi bất kỳ trong bảng để tua video đến giây tương ứng.",
                                    font=(self.FONT_NAME, 9, "italic"), bg=self.BG_MAIN, fg=self.TXT_SECONDARY)
        self.lbl_pb_hint.pack(anchor=tk.W, pady=(8, 0))

    def load_all_playback_videos(self):
        # Xóa bảng cũ
        for item in self.tree_videos.get_children():
            self.tree_videos.delete(item)
            
        # Lấy dữ liệu mới từ DB
        videos = self.db.get_all_videos()
        for v in videos:
            self.tree_videos.insert("", tk.END, values=(
                v['id'],
                v['file_name'],
                v['file_path'],
                v['upload_time'].strftime("%d/%m/%Y %H:%M:%S") if v['upload_time'] else "",
                f"{v['duration']:.1f}s" if v['duration'] else "0.0s"
            ))

    def on_video_select(self, event):
        selected_item = self.tree_videos.selection()
        if not selected_item:
            return
            
        # Đóng đầu phát video cũ nếu đang chạy
        self.stop_pb_video()
        
        item_data = self.tree_videos.item(selected_item[0])['values']
        item_id = item_data[0]
        
        if self.pb_mode == "video":
            self.pb_selected_video_path = item_data[2]  # Lấy file_path
            
            duration_str = str(item_data[4]).replace("s", "")
            self.pb_duration = float(duration_str) if duration_str else 0.0
            
            # Lấy danh sách sự kiện từ DB
            self.pb_events_list = self.db.get_video_events(item_id)
            
            # Điền bảng sự kiện hành vi
            for item in self.tree_events.get_children():
                self.tree_events.delete(item)
                
            for ev in self.pb_events_list:
                vi_name = ev['behavior_name'].replace("cat_eating", "Mèo đang ăn")\
                                             .replace("cat_sitting", "Mèo đang ngồi")\
                                             .replace("cat_sleeping", "Mèo đang ngủ")\
                                             .replace("cat_standing", "Mèo đang đứng")
                self.tree_events.insert("", tk.END, values=(
                    vi_name,
                    f"{ev['start_time']:.1f}s",
                    f"{ev['end_time']:.1f}s",
                    f"{ev['confidence']*100:.1f}%"
                ))
                
            # Bật nút Phát nếu tìm thấy file
            if os.path.exists(self.pb_selected_video_path):
                self.btn_play_pb.config(state=tk.NORMAL)
                self.lbl_time_pb.config(text=f"0.0s / {self.pb_duration:.1f}s")
                self.slider_pb.set(0)
            else:
                self.btn_play_pb.config(state=tk.DISABLED)
                self.lbl_time_pb.config(text="File nguồn đã bị di chuyển hoặc xóa")
                messagebox.showwarning("Không tìm thấy file", f"Không tìm thấy file video nguồn ở đường dẫn:\n{self.pb_selected_video_path}")
        else:
            # Chế độ Camera Live
            # Lấy danh sách sự kiện từ DB
            self.pb_events_list = self.db.get_camera_session_events(item_id)
            
            # Điền bảng sự kiện hành vi
            for item in self.tree_events.get_children():
                self.tree_events.delete(item)
                
            total_dur_calc = 0.0
            for ev in self.pb_events_list:
                vi_name = ev['behavior_name'].replace("cat_eating", "Mèo đang ăn")\
                                             .replace("cat_sitting", "Mèo đang ngồi")\
                                             .replace("cat_sleeping", "Mèo đang ngủ")\
                                             .replace("cat_standing", "Mèo đang đứng")
                
                # Tính duration
                dur = ev['duration']
                total_dur_calc += dur
                
                # Hiển thị start_time và end_time dưới dạng thời gian thực H:M:S
                start_str = ev['start_time'].strftime("%H:%M:%S") if ev['start_time'] else ""
                end_str = ev['end_time'].strftime("%H:%M:%S") if ev['end_time'] else ""
                
                self.tree_events.insert("", tk.END, values=(
                    vi_name,
                    start_str,
                    end_str,
                    f"{ev['confidence']*100:.1f}%"
                ))
            
            # Cập nhật hiển thị biểu đồ thống kê bên cạnh
            self.update_camera_stats_display(item_id, total_dur_calc)

    def switch_playback_mode(self, mode):
        self.stop_pb_video()
        self.pb_mode = mode
        
        # Xóa các dòng dữ liệu trong bảng sự kiện bên phải
        for item in self.tree_events.get_children():
            self.tree_events.delete(item)
            
        # Reset các KPI và thanh đo
        self.kpi_total_time.lbl_val.config(text="0s")
        self.kpi_major_act.lbl_val.config(text="N/A")
        for widget in self.bars_container.winfo_children():
            widget.destroy()
            
        if mode == "video":
            self.btn_pb_mode_vid.config(bg=self.ACCENT_BLUE, fg="white")
            self.btn_pb_mode_cam.config(bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY)
            
            # Thay đổi tiêu đề bảng bên trái
            self.tree_videos.heading("Tên File", text="Tên File Video")
            self.tree_videos.heading("Thời Gian", text="Thời Gian Phân Tích")
            self.tree_videos.heading("Thời Lượng", text="Độ Dài")
            
            # Pack/Unpack UI
            self.stats_frame.pack_forget()
            self.pb_video_label.pack(expand=True, fill=tk.BOTH)
            self.slider_pb.pack(fill=tk.X, padx=15, pady=(8, 4))
            self.btn_play_pb.pack(side=tk.LEFT)
            self.btn_stop_pb.pack(side=tk.LEFT, padx=10)
            self.lbl_time_pb.pack(side=tk.RIGHT, pady=5)
            self.lbl_pb_hint.config(text="* Mẹo: Nhấp đúp chuột vào một hành vi bất kỳ trong bảng để tua video đến giây tương ứng.")
            
            # Cập nhật nút Playback
            self.btn_play_pb.config(state=tk.DISABLED)
            
            # Load lại danh sách video
            self.load_all_playback_videos()
        else:
            self.btn_pb_mode_vid.config(bg=self.BG_SIDEBAR, fg=self.TXT_SECONDARY)
            self.btn_pb_mode_cam.config(bg=self.ACCENT_BLUE, fg="white")
            
            # Thay đổi tiêu đề bảng bên trái để phù hợp với Camera
            self.tree_videos.heading("Tên File", text="Tên Phiên Camera")
            self.tree_videos.heading("Thời Gian", text="Thời Gian Bắt Đầu")
            self.tree_videos.heading("Thời Lượng", text="Tổng Giám Sát")
            
            # Pack/Unpack UI
            self.pb_video_label.pack_forget()
            self.stats_frame.pack(expand=True, fill=tk.BOTH)
            
            # Ẩn thanh phát và nút điều khiển video
            self.slider_pb.pack_forget()
            self.btn_play_pb.pack_forget()
            self.btn_stop_pb.pack_forget()
            self.lbl_time_pb.pack_forget()
            self.lbl_pb_hint.config(text="* Lưu ý: Chế độ Camera Live chỉ hỗ trợ lưu nhật ký hành vi và thống kê số liệu, không có video để xem lại.")
            
            # Load danh sách session camera
            self.load_all_camera_sessions()

    def load_all_camera_sessions(self):
        # Xóa bảng cũ
        for item in self.tree_videos.get_children():
            self.tree_videos.delete(item)
            
        # Lấy dữ liệu mới từ DB
        sessions = self.db.get_all_camera_sessions()
        for s in sessions:
            # Tính tổng thời gian giám sát của session
            duration_str = "Đang chạy..."
            if s['end_time'] and s['start_time']:
                diff = (s['end_time'] - s['start_time']).total_seconds()
                hours = int(diff // 3600)
                minutes = int((diff % 3600) // 60)
                seconds = int(diff % 60)
                
                duration_str = ""
                if hours > 0:
                    duration_str += f"{hours}h "
                if minutes > 0 or hours > 0:
                    duration_str += f"{minutes}m "
                duration_str += f"{seconds}s"
            
            self.tree_videos.insert("", tk.END, values=(
                s['id'],
                s['session_name'],
                s['status'], # Cột ẩn
                s['start_time'].strftime("%d/%m/%Y %H:%M:%S") if s['start_time'] else "",
                duration_str
            ))

    def setup_stats_ui(self):
        # Tiêu đề báo cáo số liệu
        lbl_stats_title = tk.Label(self.stats_frame, text="PHÂN TÍCH HOẠT ĐỘNG CAMERA LIVE", 
                                   font=(self.FONT_NAME, 13, "bold"), bg=self.BG_CARD, fg=self.ACCENT_BLUE)
        lbl_stats_title.pack(anchor=tk.W, padx=20, pady=(15, 5))
        
        # Thẻ chứa các chỉ số tổng quan (KPIs)
        kpi_container = tk.Frame(self.stats_frame, bg=self.BG_CARD)
        kpi_container.pack(fill=tk.X, padx=20, pady=5)
        
        # KPI 1: Tổng thời gian giám sát
        self.kpi_total_time = self.create_kpi_card(kpi_container, "TỔNG THỜI GIAN", "0s", self.ACCENT_BLUE)
        self.kpi_total_time.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # KPI 2: Hoạt động nhiều nhất
        self.kpi_major_act = self.create_kpi_card(kpi_container, "HOẠT ĐỘNG CHỦ ĐẠO", "N/A", self.ACCENT_EMERALD)
        self.kpi_major_act.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Thẻ chứa các thanh đo hành vi
        self.bars_container = tk.LabelFrame(self.stats_frame, text="TỶ LỆ PHÂN BỔ HÀNH VI MÈO", font=(self.FONT_NAME, 9, "bold"),
                                            bg=self.BG_CARD, fg=self.TXT_SECONDARY, labelanchor=tk.NW,
                                            highlightthickness=1, highlightbackground=self.BORDER_COLOR, bd=0)
        self.bars_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 15))

    def create_kpi_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg="#0b0f19", highlightthickness=1, highlightbackground=self.BORDER_COLOR, padx=10, pady=8)
        
        lbl_title = tk.Label(card, text=title, font=(self.FONT_NAME, 8, "bold"), bg="#0b0f19", fg=self.TXT_SECONDARY)
        lbl_title.pack(anchor=tk.W)
        
        lbl_val = tk.Label(card, text=value, font=(self.FONT_NAME, 13, "bold"), bg="#0b0f19", fg=color)
        lbl_val.pack(anchor=tk.W, pady=(2, 0))
        
        # Lưu tham chiếu để cập nhật động sau này
        card.lbl_val = lbl_val
        return card

    def update_camera_stats_display(self, session_id, duration_total):
        # Xóa các widget thanh đo cũ
        for widget in self.bars_container.winfo_children():
            widget.destroy()
            
        stats = self.db.get_camera_behavior_stats(session_id)
        
        # Chuyển đổi định dạng tổng thời gian giám sát
        if duration_total > 0:
            hours = int(duration_total // 3600)
            minutes = int((duration_total % 3600) // 60)
            seconds = int(duration_total % 60)
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours}h "
            if minutes > 0 or hours > 0:
                time_str += f"{minutes}m "
            time_str += f"{seconds}s"
        else:
            time_str = "0s"
            
        self.kpi_total_time.lbl_val.config(text=time_str)
        
        if not stats or duration_total == 0:
            self.kpi_major_act.lbl_val.config(text="CHƯA CÓ DỮ LIỆU")
            tk.Label(self.bars_container, text="Không phát hiện hành vi nào trong phiên này",
                     font=(self.FONT_NAME, 10), bg=self.BG_CARD, fg=self.TXT_SECONDARY).pack(expand=True)
            return
            
        # Tìm hành vi chiếm thời gian nhiều nhất
        max_stat = max(stats, key=lambda x: x['total_duration'])
        vi_major_name = max_stat['behavior_name'].replace("cat_eating", "Ăn uống")\
                                                 .replace("cat_sitting", "Ngồi chơi")\
                                                 .replace("cat_sleeping", "Ngủ nghỉ")\
                                                 .replace("cat_standing", "Đứng quan sát")
        self.kpi_major_act.lbl_val.config(text=vi_major_name.upper())
        
        # Định nghĩa màu sắc cho các hành vi
        color_map = {
            'cat_eating': self.ACCENT_EMERALD,
            'cat_sitting': self.ACCENT_YELLOW,
            'cat_sleeping': self.ACCENT_BLUE,
            'cat_standing': "#f97316" # Cam
        }
        
        label_map = {
            'cat_eating': "Mèo đang ăn (Ăn uống)",
            'cat_sitting': "Mèo đang ngồi (Ngồi chơi)",
            'cat_sleeping': "Mèo đang ngủ (Ngủ nghỉ)",
            'cat_standing': "Mèo đang đứng (Quan sát)"
        }
        
        # Vẽ các thanh tiến trình cho từng hành vi
        for i, item in enumerate(stats):
            b_name = item['behavior_name']
            dur = item['total_duration']
            pct = (dur / duration_total) * 100
            
            color = color_map.get(b_name, self.TXT_SECONDARY)
            label = label_map.get(b_name, b_name)
            
            # Format thời gian hành vi này
            m_dur = int(dur // 60)
            s_dur = int(dur % 60)
            dur_str = f"{m_dur}m {s_dur}s" if m_dur > 0 else f"{s_dur}s"
            
            # Frame chứa 1 dòng hành vi
            row_frame = tk.Frame(self.bars_container, bg=self.BG_CARD)
            row_frame.pack(fill=tk.X, padx=15, pady=8)
            
            # Label nhãn và thời lượng
            info_frame = tk.Frame(row_frame, bg=self.BG_CARD)
            info_frame.pack(fill=tk.X)
            
            tk.Label(info_frame, text=label, font=(self.FONT_NAME, 9, "bold"), bg=self.BG_CARD, fg=self.TXT_PRIMARY).pack(side=tk.LEFT)
            tk.Label(info_frame, text=f"{dur_str} ({pct:.1f}%)", font=(self.FONT_NAME, 9, "bold"), bg=self.BG_CARD, fg=color).pack(side=tk.RIGHT)
            
            # Thanh tiến trình đồ họa tự chế (Premium)
            bar_bg = tk.Frame(row_frame, bg="#0b0f19", height=8, highlightthickness=0)
            bar_bg.pack(fill=tk.X, pady=(4, 0))
            bar_bg.pack_propagate(False)
            
            # Thanh phần trăm màu sắc
            bar_fg = tk.Frame(bar_bg, bg=color, height=8)
            bar_fg.place(x=0, y=0, relwidth=pct/100.0, relheight=1)

    def toggle_pb_pause(self):
        if not self.is_pb_running:
            self.start_pb_video()
        else:
            self.is_pb_paused = not self.is_pb_paused
            if self.is_pb_paused:
                self.btn_play_pb.config(text="▶ TIẾP TỤC", bg=self.ACCENT_EMERALD)
            else:
                self.btn_play_pb.config(text="⏸ TẠM DỪNG", bg=self.ACCENT_YELLOW)
                self.update_pb_frame()

    def start_pb_video(self):
        if hasattr(self, 'pb_selected_video_path') and self.pb_selected_video_path:
            self.pb_selected_video_path_safe = self.get_safe_video_path(self.pb_selected_video_path)
            self.pb_cap = cv2.VideoCapture(self.pb_selected_video_path_safe)
            if not self.pb_cap.isOpened():
                messagebox.showerror("Lỗi", "Không thể mở file video để xem lại!")
                return
            
            # Đọc FPS thực tế của video để đồng bộ tốc độ chạy xem lại
            fps = self.pb_cap.get(cv2.CAP_PROP_FPS)
            self.pb_fps = fps if fps > 0 else 30.0
            self.pb_delay = int(1000 / self.pb_fps)

            self.is_pb_running = True
            self.is_pb_paused = False
            self.btn_play_pb.config(text="⏸ TẠM DỪNG", bg=self.ACCENT_YELLOW)
            self.btn_stop_pb.config(state=tk.NORMAL)
            self.update_pb_frame()

    def update_pb_frame(self):
        if self.is_pb_running and self.pb_cap and not self.is_pb_paused:
            start_time_proc = datetime.now()
            ret, frame = self.pb_cap.read()
            if ret:
                # Tự động thay đổi kích thước theo khung hiển thị thực tế để tránh bị cắt chữ
                pw = self.pb_video_label.master.winfo_width()
                ph = self.pb_video_label.master.winfo_height()
                w_target = pw if pw > 100 else 640
                h_target = ph if ph > 100 else 480
                frame = cv2.resize(frame, (w_target, h_target))
                
                # Tính thời gian hiện tại chuẩn xác dựa trên số khung hình (tránh lỗi lệch giây của OpenCV)
                current_frame = self.pb_cap.get(cv2.CAP_PROP_POS_FRAMES)
                current_time = current_frame / self.pb_fps
                
                # Truy tìm sự kiện tương thích lưu trong DB để overlay nhãn
                active_event = None
                for ev in self.pb_events_list:
                    if ev['start_time'] <= current_time <= ev['end_time']:
                        active_event = ev
                        break
                        
                # Vẽ đè thông tin AI
                if active_event:
                    vi_name = active_event['behavior_name'].replace("cat_eating", "Mèo đang ăn")\
                                                           .replace("cat_sitting", "Mèo đang ngồi")\
                                                           .replace("cat_sleeping", "Mèo đang ngủ")\
                                                           .replace("cat_standing", "Mèo đang đứng")
                    self.draw_pb_overlay(frame, vi_name, active_event['confidence'] * 100)
                else:
                    self.draw_pb_overlay(frame, "Không phát hiện hành vi", 0, is_empty=True)

                self.display_pb_frame(frame)
                
                # Cập nhật vị trí scale bar nếu người dùng đang không kéo slider
                if not self.is_pb_seeking and self.pb_duration > 0:
                    percent = (current_time / self.pb_duration) * 100
                    self.slider_pb.set(percent)
                    self.lbl_time_pb.config(text=f"{current_time:.1f}s / {self.pb_duration:.1f}s")
                
                # Bù thời gian vẽ đè overlay và resize hình ảnh
                proc_time_ms = int((datetime.now() - start_time_proc).total_seconds() * 1000)
                delay = max(1, self.pb_delay - proc_time_ms)
                self.root.after(delay, self.update_pb_frame)
            else:
                self.stop_pb_video()

    def draw_pb_overlay(self, frame, text, confidence, is_empty=False):
        h, w, _ = frame.shape
        # Vẽ một thanh nền đen trong suốt ở cạnh dưới của video bằng OpenCV
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 50), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        
        # Viết nhãn hành vi
        if is_empty:
            label_text = f"AI Playback: {text}"
            pil_color = "#94a3b8"  # Slate Gray
        else:
            label_text = f"AI Playback: {text} (Độ tin cậy: {confidence:.1f}%)"
            pil_color = "#10b981"  # Emerald Green
            
        # Sử dụng PIL để vẽ chữ Unicode sắc nét, hỗ trợ Tiếng Việt
        try:
            import numpy as np
            # Chuyển OpenCV frame (BGR) sang PIL Image (RGB)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)
            
            # Cấu hình Font hỗ trợ Tiếng Việt
            font_path = "C:\\Windows\\Fonts\\segoeuib.ttf"  # Segoe UI Bold
            if not os.path.exists(font_path):
                font_path = "C:\\Windows\\Fonts\\arial.ttf"  # Arial
                
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 15)
            else:
                font = None
                
            # Vẽ văn bản
            draw.text((20, h - 36), label_text, font=font, fill=pil_color)
            
            # Chuyển PIL Image quay lại thành OpenCV frame (BGR)
            frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            # Fallback về putText nếu có lỗi thư viện
            print(f"Lỗi vẽ chữ Unicode bằng PIL: {e}")
            cv2.putText(frame, label_text, (20, h - 18), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184) if is_empty else (16, 185, 129), 2, cv2.LINE_AA)

    def display_pb_frame(self, frame):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img_tk = ImageTk.PhotoImage(image=img)
        self.pb_video_label.imgtk = img_tk
        self.pb_video_label.configure(image=img_tk)

    def stop_pb_video(self):
        self.is_pb_running = False
        self.is_pb_paused = False
        if self.pb_cap:
            self.pb_cap.release()
            self.pb_cap = None
        self.pb_video_label.config(image=self.standby_image)
        self.btn_play_pb.config(text="▶ PHÁT", bg=self.ACCENT_EMERALD)
        self.btn_stop_pb.config(state=tk.DISABLED)
        self.slider_pb.set(0)
        if hasattr(self, 'pb_duration'):
            self.lbl_time_pb.config(text=f"0.0s / {self.pb_duration:.1f}s")
        else:
            self.lbl_time_pb.config(text="0.0s / 0.0s")

    def on_slider_drag(self, event):
        # Trực quan hóa thời gian tạm thời khi người dùng nhấn giữ kéo
        if hasattr(self, 'pb_duration') and self.pb_duration > 0:
            self.is_pb_seeking = True
            val = self.slider_pb.get()
            percent = float(val) / 100.0
            sec = percent * self.pb_duration
            self.lbl_time_pb.config(text=f"{sec:.1f}s / {self.pb_duration:.1f}s")

    def on_slider_release(self, event):
        # Khi nhả chuột ra thì tua video đến giây tương ứng và tiếp tục phát
        if self.pb_cap and hasattr(self, 'pb_duration') and self.pb_duration > 0:
            val = self.slider_pb.get()
            percent = float(val) / 100.0
            pos_ms = percent * self.pb_duration * 1000.0
            self.pb_cap.set(cv2.CAP_PROP_POS_MSEC, pos_ms)
            
            # Cập nhật frame hình tại giây được tua ngay lập tức
            ret, frame = self.pb_cap.read()
            if ret:
                # Tự động thay đổi kích thước theo khung hiển thị thực tế
                pw = self.pb_video_label.master.winfo_width()
                ph = self.pb_video_label.master.winfo_height()
                w_target = pw if pw > 100 else 640
                h_target = ph if ph > 100 else 480
                frame = cv2.resize(frame, (w_target, h_target))
                current_time = pos_ms / 1000.0
                active_event = None
                for ev in self.pb_events_list:
                    if ev['start_time'] <= current_time <= ev['end_time']:
                        active_event = ev
                        break
                        
                # Vẽ đè thông tin AI
                if active_event:
                    vi_name = active_event['behavior_name'].replace("cat_eating", "Mèo đang ăn")\
                                                           .replace("cat_sitting", "Mèo đang ngồi")\
                                                           .replace("cat_sleeping", "Mèo đang ngủ")\
                                                           .replace("cat_standing", "Mèo đang đứng")
                    self.draw_pb_overlay(frame, vi_name, active_event['confidence'] * 100)
                else:
                    self.draw_pb_overlay(frame, "Không phát hiện hành vi", 0, is_empty=True)

                self.display_pb_frame(frame)
                
                # Cập nhật vị trí scale bar nếu người dùng đang không kéo slider
                if not self.is_pb_seeking and self.pb_duration > 0:
                    percent = (current_time / self.pb_duration) * 100
                    self.slider_pb.set(percent)
                    self.lbl_time_pb.config(text=f"{current_time:.1f}s / {self.pb_duration:.1f}s")
                
                # Bù thời gian vẽ đè overlay và resize hình ảnh
                proc_time_ms = int((datetime.now() - start_time_proc).total_seconds() * 1000)
                delay = max(1, self.pb_delay - proc_time_ms)
                self.root.after(delay, self.update_pb_frame)
            else:
                self.stop_pb_video()

    def on_event_double_click(self, event):
        if hasattr(self, 'pb_mode') and self.pb_mode == "camera":
            return
            
        selected_item = self.tree_events.selection()
        if not selected_item:
            return
        item_data = self.tree_events.item(selected_item[0])['values']
        start_time = float(item_data[1].replace("s", ""))
        
        # Nếu chưa chạy video thì bắt đầu chạy
        if not self.is_pb_running:
            self.start_pb_video()
            
        if self.pb_cap:
            pos_ms = start_time * 1000.0
            self.pb_cap.set(cv2.CAP_PROP_POS_MSEC, pos_ms)
            
            # Cập nhật hiển thị frame ngay lập tức
            ret, frame = self.pb_cap.read()
            if ret:
                # Tự động thay đổi kích thước theo khung hiển thị thực tế
                pw = self.pb_video_label.master.winfo_width()
                ph = self.pb_video_label.master.winfo_height()
                w_target = pw if pw > 100 else 640
                h_target = ph if ph > 100 else 480
                frame = cv2.resize(frame, (w_target, h_target))
                vi_name = item_data[0]
                conf = float(item_data[3].replace("%", ""))
                self.draw_pb_overlay(frame, vi_name, conf)
                self.display_pb_frame(frame)

    def btn_cam_toggle_ai_normal_color(self):
        if hasattr(self, 'cam_ai_active') and self.cam_ai_active:
            return self.ACCENT_YELLOW
        return self.ACCENT_BLUE
        
    def btn_cam_toggle_ai_hover_color(self):
        if hasattr(self, 'cam_ai_active') and self.cam_ai_active:
            return self.ACCENT_YELLOW_HOVER
        return self.ACCENT_BLUE_HOVER

    def toggle_cam_ai(self):
        if self.is_running and not self.is_video_mode:
            self.cam_ai_active = not self.cam_ai_active
            if self.cam_ai_active:
                self.btn_cam_toggle_ai.config(text="⏸ TẠM DỪNG AI", bg=self.ACCENT_YELLOW)
                self.lbl_cam_status.config(text="● ĐANG GIÁM SÁT REAL-TIME + AI", fg=self.ACCENT_EMERALD)
                self.write_log("Hệ thống: Kích hoạt nhận diện AI trên luồng Camera.")
                # Reset mốc thời gian bắt đầu hành vi mới
                self.last_cam_behavior_raw = None
                self.cam_event_start_dt = datetime.now()
                self.cam_conf_list = []
            else:
                self.btn_cam_toggle_ai.config(text="🤖 BẬT AI NHẬN DẠNG", bg=self.ACCENT_BLUE)
                self.lbl_cam_status.config(text="● ĐANG HIỂN THỊ CAMERA THƯỜNG", fg=self.ACCENT_BLUE)
                self.write_log("Hệ thống: Tạm dừng nhận diện AI.")
                
                # Lưu hành vi dở dang khi tắt AI
                if self.last_cam_behavior_raw and self.current_session_id:
                    end_dt = datetime.now()
                    duration = (end_dt - self.cam_event_start_dt).total_seconds()
                    avg_conf = sum(self.cam_conf_list) / len(self.cam_conf_list) if self.cam_conf_list else 0
                    self.db.insert_camera_event(
                        self.current_session_id, self.last_cam_behavior_raw,
                        self.cam_event_start_dt, end_dt, duration, avg_conf
                    )
                    self.write_log(f"[DB] Ghi DB Camera: {self.last_cam_behavior_raw.replace('cat_eating', 'Mèo đang ăn').replace('cat_sitting', 'Mèo đang ngồi').replace('cat_sleeping', 'Mèo đang ngủ').replace('cat_standing', 'Mèo đang đứng')} ({duration:.1f}s)")
                
                self.last_cam_behavior_raw = None
                self.cam_event_start_dt = None
                self.cam_conf_list = []
                self.update_live_badge(is_video=False, behavior_raw=None, conf=0.0)

    def update_frame(self):
        if self.is_running and self.cap and not self.is_paused:
            start_time_proc = datetime.now()
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (640, 480))
                
                # Xác định có chạy mô hình AI nhận diện không
                run_ai = True
                if not self.is_video_mode and not self.cam_ai_active:
                    run_ai = False
                    
                if run_ai:
                    results = self.model(frame, verbose=False)
                    annotated_frame = results[0].plot()
    
                    current_behavior = "None"
                    current_behavior_raw = None
                    current_conf = 0.0
    
                    if len(results[0].boxes) > 0:
                        conf = float(results[0].boxes[0].conf[0])
                        if conf >= 0.75:
                            class_id = int(results[0].boxes[0].cls[0])
                            current_behavior_raw = self.model.names[class_id]
                            current_behavior = f"{current_behavior_raw} ({conf*100:.0f}%)"
                            current_conf = conf
                else:
                    annotated_frame = frame.copy()
                    current_behavior = "None"
                    current_behavior_raw = None
                    current_conf = 0.0

                # Cập nhật Live Status Dashboard Card
                self.update_live_badge(self.is_video_mode, current_behavior_raw, current_conf)

                # Hiển thị nhật ký log lên khung giao diện (chỉ ghi khi AI đang chạy)
                if run_ai:
                    if current_behavior != "None" and current_behavior != self.last_behavior:
                        vi_label = current_behavior.replace("cat_eating", "Mèo đang ăn")\
                                                   .replace("cat_sitting", "Mèo đang ngồi")\
                                                   .replace("cat_sleeping", "Mèo đang ngủ")\
                                                   .replace("cat_standing", "Mèo đang đứng")
                        self.write_log(f"Phát hiện: {vi_label}", is_video=self.is_video_mode)
                        self.last_behavior = current_behavior
                    elif current_behavior == "None" and self.last_behavior is not None:
                        self.write_log("Trạng thái: Không tìm thấy đối tượng", is_video=self.is_video_mode)
                        self.last_behavior = None

                # --- LOGIC LƯU DATABASE KHI PHÂN TÍCH VIDEO ---
                if self.is_video_mode:
                    current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                    current_v_time = current_frame / self.fps
                    
                    if current_behavior_raw != self.last_behavior_raw_db:
                        # 1. Lưu khoảng hành vi cũ vừa kết thúc vào DB
                        if self.last_behavior_raw_db and self.current_video_id:
                            avg_conf = sum(self.conf_list) / len(self.conf_list) if self.conf_list else 0
                            self.db.insert_behavior_event(
                                self.current_video_id, self.last_behavior_raw_db,
                                self.event_start_time, current_v_time, avg_conf
                            )
                            self.write_log(f"[DB] Ghi DB: {self.last_behavior_raw_db} ({self.event_start_time:.1f}s -> {current_v_time:.1f}s)", is_video=True)
                        
                        # 2. Chuyển sang theo dõi hành vi mới
                        self.last_behavior_raw_db = current_behavior_raw
                        self.event_start_time = current_v_time
                        self.conf_list = [current_conf] if current_behavior_raw else []
                    else:
                        # Đang tiếp tục hành vi cũ, thu thập độ tin cậy để tính trung bình
                        if current_behavior_raw:
                            self.conf_list.append(current_conf)
                else:
                    # --- LOGIC LƯU DATABASE KHI CHẠY CAMERA TRỰC TIẾP (Chỉ ghi khi AI active) ---
                    if self.cam_ai_active:
                        if current_behavior_raw != self.last_cam_behavior_raw:
                            # 1. Lưu khoảng hành vi cũ vừa kết thúc vào DB
                            if self.last_cam_behavior_raw and self.current_session_id:
                                end_dt = datetime.now()
                                duration = (end_dt - self.cam_event_start_dt).total_seconds()
                                avg_conf = sum(self.cam_conf_list) / len(self.cam_conf_list) if self.cam_conf_list else 0
                                self.db.insert_camera_event(
                                    self.current_session_id, self.last_cam_behavior_raw,
                                    self.cam_event_start_dt, end_dt, duration, avg_conf
                                )
                                self.write_log(f"[DB] Ghi DB Camera: {self.last_cam_behavior_raw.replace('cat_eating', 'Mèo đang ăn').replace('cat_sitting', 'Mèo đang ngồi').replace('cat_sleeping', 'Mèo đang ngủ').replace('cat_standing', 'Mèo đang đứng')} ({duration:.1f}s)")
                            
                            # 2. Chuyển sang theo dõi hành vi mới
                            self.last_cam_behavior_raw = current_behavior_raw
                            self.cam_event_start_dt = datetime.now()
                            self.cam_conf_list = [current_conf] if current_behavior_raw else []
                        else:
                            # Đang tiếp tục hành vi cũ, thu thập độ tin cậy để tính trung bình
                            if current_behavior_raw:
                                self.cam_conf_list.append(current_conf)

                # Chuyển đổi màu và đẩy frame hình lên GUI
                img = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img_tk = ImageTk.PhotoImage(image=img)
                
                display_label = self.vid_display_frame if self.is_video_mode else self.cam_video_frame
                display_label.imgtk = img_tk
                display_label.configure(image=img_tk)
                
                # Bù thời gian suy luận YOLO
                proc_time_ms = int((datetime.now() - start_time_proc).total_seconds() * 1000)
                if self.is_video_mode:
                    delay = max(1, self.analysis_delay - proc_time_ms)
                else:
                    delay = 15  # Camera chế độ thời gian thực
                self.root.after(delay, self.update_frame)
            else:
                if self.is_video_mode:
                    # Lưu hành vi dở dang cuối cùng trước khi hết video
                    if self.last_behavior_raw_db and self.current_video_id:
                        end_time = self.video_duration
                        avg_conf = sum(self.conf_list) / len(self.conf_list) if self.conf_list else 0
                        self.db.insert_behavior_event(
                            self.current_video_id, self.last_behavior_raw_db,
                            self.event_start_time, end_time, avg_conf
                        )
                        self.write_log(f"[DB] Ghi DB: {self.last_behavior_raw_db} ({self.event_start_time:.1f}s -> {end_time:.1f}s)", is_video=True)
                        self.last_behavior_raw_db = None
                        
                    self.write_log("Hệ thống: Đã hoàn tất phân tích toàn bộ video.", is_video=True)
                    self.stop_video()
                else:
                    self.stop_camera()

if __name__ == "__main__":
    root = tk.Tk()
    app = CatBehaviorApp(root)
    root.mainloop()
