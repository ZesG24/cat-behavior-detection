import pytest
import os
from datetime import datetime
from database_manager import DatabaseManager

# Fixture dùng để khởi tạo Database Test và tự động dọn dẹp sau khi chạy xong
@pytest.fixture(scope="module")
def db_manager():
    db = DatabaseManager(database="CatBehaviorAI_Pytest_Test")
    
    # Tạo database test
    import mysql.connector
    conn = mysql.connector.connect(
        host=db.config['host'],
        user=db.config['user'],
        password=db.config['password']
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS CatBehaviorAI_Pytest_Test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.close()
    conn.close()
    
    # Kết nối tạo bảng
    success, msg = db.test_connection()
    if not success:
        pytest.skip(f"Bỏ qua test do lỗi kết nối MySQL: {msg}")
        
    yield db  # Trả về đối tượng db để các hàm test sử dụng
    
    # tearDown: Dọn dẹp CSDL test sau khi toàn bộ file test chạy xong
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP DATABASE IF EXISTS CatBehaviorAI_Pytest_Test;")
        conn.commit()
        cursor.close()
        conn.close()
        print("\n[INFO] Đã xóa database kiểm thử của Pytest.")
    except Exception as e:
        print(f"\n[WARNING] Lỗi dọn dẹp: {e}")

# --- CÁC BÀI TEST CHỨC NĂNG ---

def test_connection(db_manager):
    assert db_manager.config['database'] == "CatBehaviorAI_Pytest_Test"

def test_insert_and_get_video(db_manager):
    test_hash = "pytest_hash_123"
    video_id = db_manager.insert_video("test_pytest.mp4", "D:/test.mp4", test_hash, 20.0)
    
    assert video_id is not None
    
    video_rec = db_manager.get_video_by_hash(test_hash)
    assert video_rec is not None
    assert video_rec['id'] == video_id

def test_camera_session_flow(db_manager):
    session_id = db_manager.insert_camera_session("Pytest Cam Session")
    assert session_id is not None
    
    start_dt = datetime.now()
    end_dt = datetime.now()
    db_manager.insert_camera_event(session_id, "cat_eating", start_dt, end_dt, 10.0, 0.90)
    
    stats = db_manager.get_camera_behavior_stats(session_id)
    assert len(stats) == 1
    assert stats[0]['behavior_name'] == "cat_eating"
    
    success = db_manager.end_camera_session(session_id)
    assert success is True
