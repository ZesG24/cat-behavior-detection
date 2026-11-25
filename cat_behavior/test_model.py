import os
from ultralytics import YOLO

def main():
    # Xác định thư mục gốc của dự án (d:\AIThayKhue)
    # Vì file này nằm ở d:\AIThayKhue\cat_behavior\test_model.py nên:
    # os.path.abspath(__file__) -> d:\AIThayKhue\cat_behavior\test_model.py
    # os.path.dirname(os.path.abspath(__file__)) -> d:\AIThayKhue\cat_behavior
    # Lấy thêm 1 lần dirname nữa để ra thư mục gốc d:\AIThayKhue
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Đường dẫn tuyệt đối đến file weights
    best_model_path = os.path.join(BASE_DIR, "runs", "detect", "cat_behavior_v1", "weights", "best.pt")
    
    # Đường dẫn tuyệt đối đến file data.yaml
    yaml_path = os.path.join(BASE_DIR, "Cat_behavior-1", "data.yaml")
    
    print("==================================================")
    print("KIỂM TRA ĐƯỜNG DẪN:")
    print(f" - Đường dẫn mô hình: {best_model_path}")
    print(f" - Đường dẫn data.yaml: {yaml_path}")
    print("==================================================")
    
    if not os.path.exists(best_model_path):
        print(f"Lỗi: Không tìm thấy file model tại: {best_model_path}")
        return
        
    if not os.path.exists(yaml_path):
        print(f"Lỗi: Không tìm thấy file cấu hình dữ liệu tại: {yaml_path}")
        return
        
    print("\n--- BẮT ĐẦU TẢI MÔ HÌNH ---")
    model = YOLO(best_model_path)
    
    print("\n--- BẮT ĐẦU ĐÁNH GIÁ TRÊN TẬP TEST ---")
    # Đánh giá độc lập trên tập test
    # name='test_evaluation' để lưu các ảnh test đã dự đoán vào runs/detect/test_evaluation/
    metrics = model.val(
        data=yaml_path,
        split='test',
        name='test_evaluation'
    )
    
    print("\n================ KẾT QUẢ TRÊN TẬP TEST ================")
    print(f"Độ chính xác mAP50: {metrics.box.map50:.4f}")
    print(f"Độ chính xác mAP50-95: {metrics.box.map:.4f}")
    print(f"Các ảnh kết quả dự đoán (val_batch*_pred.jpg) đã được lưu tại thư mục:")
    print(f" -> {os.path.join(BASE_DIR, 'runs', 'detect', 'test_evaluation')}")
    print("=======================================================")

if __name__ == '__main__':
    main()
