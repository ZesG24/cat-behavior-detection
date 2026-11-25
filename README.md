# Cat Behavior AI (YOLOv8 + Tkinter + MySQL)

Ứng dụng nhận diện và theo dõi hành vi mèo (`cat_eating`, `cat_sitting`, `cat_sleeping`, `cat_standing`) theo thời gian thực qua Camera hoặc Video bằng YOLOv8, lưu lịch sử vào MySQL.

## Yêu cầu hệ thống
- Python 3.9+
- MySQL Server (XAMPP, Laragon, hoặc MySQL cài đặt độc lập)

## Cài đặt
1. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```
2. Khởi tạo cơ sở dữ liệu bằng file `db.txt` trong MySQL (`CatBehaviorAI`).
3. Kiểm tra cấu hình kết nối MySQL trong `cat_behavior/database_manager.py` (mặc định `host="localhost"`, `user="root"`, `password=""`).

## Chạy ứng dụng
Chạy trực tiếp file `run_app.bat` hoặc từ terminal:
```bash
cd cat_behavior
python app_gui.py
```

## Huấn luyện & Kiểm thử
- **Huấn luyện lại mô hình**: Thiết lập biến môi trường `ROBOFLOW_API_KEY` rồi chạy `python cat_behavior/train_cat.py`.
- **Đánh giá mô hình**: `python cat_behavior/test_model.py`
- **Unit test database**: `pytest cat_behavior/test_database.py` (cần bật MySQL trước).
