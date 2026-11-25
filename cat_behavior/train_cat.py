from roboflow import Roboflow
from ultralytics import YOLO
import os

def main():
    print("--- BƯỚC 1: TẢI DỮ LIỆU TỪ ROBOFLOW (CAT BEHAVIOR V1) ---")
    # Khởi tạo Roboflow với API Key từ biến môi trường ROBOFLOW_API_KEY
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        raise ValueError("Vui lòng thiết lập biến môi trường ROBOFLOW_API_KEY trước khi chạy.")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace("vinhvdp24-gmail-com").project("cat_behavior-bujsd")
    
    # Tải version 1
    version = project.version(1)
    dataset = version.download("yolov8")
    
    print(f"\n--- Đã tải xong dữ liệu tại: {dataset.location} ---")
    yaml_path = os.path.join(dataset.location, "data.yaml")

    print("\n--- BƯỚC 2: BẮT ĐẦU HUẤN LUYỆN (TRAIN) 100 EPOCHS ---")
    # Sử dụng yolov8n.pt (bản Nano) để chạy nhanh và nhẹ
    model = YOLO('yolov8n.pt') 

    # Bắt đầu huấn luyện
    # - epochs=100: Số vòng lặp tối đa
    # - imgsz=640: Kích thước ảnh chuẩn
    # - batch=16: Số ảnh mỗi lần xử lý (tăng lên 32 nếu có GPU mạnh)
    # - patience=20: Tự động dừng nếu 20 vòng không cải thiện
    results = model.train(
        data=yaml_path,
        epochs=100,
        imgsz=640,
        batch=16,
        patience=20,
        name='cat_behavior_v1',   # Tên thư mục kết quả
        device='cpu'              # Mặc định dùng CPU, đổi thành 0 nếu có GPU NVIDIA
    )
    
    print("\n--- BƯỚC 3: KIỂM TRA ĐỘ CHÍNH XÁC TRÊN TẬP TEST ---")
    # Load model tốt nhất vừa train xong
    best_model_path = "runs/detect/cat_behavior_v1/weights/best.pt"
    if os.path.exists(best_model_path):
        best_model = YOLO(best_model_path)
        
        # Đánh giá trên tập test (độc lập hoàn toàn)
        print("Đang đánh giá trên tập dữ liệu TEST...")
        metrics = best_model.val(split='test')
        
        print("\n=== KẾT QUẢ CUỐI CÙNG TRÊN TẬP TEST ===")
        print(f"Độ chính xác mAP50: {metrics.box.map50:.3f}")
        print(f"Độ chính xác mAP50-95: {metrics.box.map:.3f}")
        print(f"Mô hình lưu tại: {best_model_path}")
    else:
        print("Lỗi: Không tìm thấy file model sau khi train!")

if __name__ == '__main__':
    main()
