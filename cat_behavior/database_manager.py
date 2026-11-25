import mysql.connector
import os

class DatabaseManager:
    def __init__(self, host="localhost", user="root", password="", database="CatBehaviorAI"):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'auth_plugin': 'mysql_native_password' 
        }

    def convert_to_utf8(self):
        """Chuyển đổi database và các bảng sang charset utf8mb4 để hỗ trợ đầy đủ Tiếng Việt"""
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            # Đổi charset database
            cursor.execute("ALTER DATABASE CatBehaviorAI CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            
            # Đổi charset các bảng
            cursor.execute("ALTER TABLE Videos CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute("ALTER TABLE Behaviors CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute("ALTER TABLE BehaviorEvents CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            
            try:
                cursor.execute("ALTER TABLE CameraSessions CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                cursor.execute("ALTER TABLE CameraEvents CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            except Exception as e_tables:
                print(f"MySQL: Lỗi đổi charset bảng camera mới (bảng chưa tạo?): {e_tables}")
            
            conn.commit()
            cursor.close()
            conn.close()
            print("MySQL: Tối ưu hóa charset utf8mb4 thành công.")
        except Exception as e:
            print(f"MySQL: Lỗi chuyển đổi charset sang utf8mb4: {e}")

    def test_connection(self):
        """Kiem tra ket noi toi Database"""
        try:
            conn = mysql.connector.connect(**self.config)
            conn.close()
            
            # Tự động tạo các bảng nếu chưa có
            self.create_tables_if_not_exists()
            # Chạy tự động chuyển đổi bảng khi kết nối
            self.convert_to_utf8()
            
            return True, "Database connection success"
        except Exception as e:
            return False, str(e)

    def create_tables_if_not_exists(self):
        """Tự động tạo các bảng nếu chưa tồn tại trong database"""
        try:
            # Tạo kết nối trực tiếp
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 1. Bảng Videos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Videos (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    video_hash VARCHAR(255) UNIQUE,
                    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    duration FLOAT
                );
            """)
            
            # 2. Bảng Behaviors
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Behaviors (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    behavior_name VARCHAR(100) NOT NULL UNIQUE
                );
            """)
            
            # 3. Bảng BehaviorEvents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS BehaviorEvents (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    video_id INT NOT NULL,
                    behavior_id INT NOT NULL,
                    start_time FLOAT NOT NULL,
                    end_time FLOAT NOT NULL,
                    confidence FLOAT,
                    CONSTRAINT FK_Video FOREIGN KEY (video_id) REFERENCES Videos(id) ON DELETE CASCADE,
                    CONSTRAINT FK_Behavior FOREIGN KEY (behavior_id) REFERENCES Behaviors(id)
                );
            """)
            
            # 4. Bảng CameraSessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS CameraSessions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    session_name VARCHAR(255) NOT NULL,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME NULL,
                    status VARCHAR(50) DEFAULT 'running'
                );
            """)
            
            # 5. Bảng CameraEvents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS CameraEvents (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    session_id INT NOT NULL,
                    behavior_id INT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    duration FLOAT NOT NULL,
                    confidence FLOAT,
                    CONSTRAINT FK_CameraSession FOREIGN KEY (session_id) REFERENCES CameraSessions(id) ON DELETE CASCADE,
                    CONSTRAINT FK_CameraBehavior FOREIGN KEY (behavior_id) REFERENCES Behaviors(id)
                );
            """)
            
            # Khởi tạo dữ liệu mẫu cho Behaviors
            behaviors = [('cat_eating',), ('cat_sitting',), ('cat_sleeping',), ('cat_standing',)]
            cursor.executemany("INSERT IGNORE INTO Behaviors (behavior_name) VALUES (%s)", behaviors)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("MySQL: Tự động khởi tạo cấu trúc bảng thành công.")
        except Exception as e:
            print(f"MySQL: Lỗi tự động khởi tạo bảng: {e}")

    def _get_connection(self):
        return mysql.connector.connect(**self.config)

    def get_video_by_hash(self, v_hash):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM Videos WHERE video_hash = %s", (v_hash,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result
        except Exception as e:
            print(f"DB Error (get_video): {e}")
            return None

    def insert_video(self, name, path, v_hash, duration):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO Videos (file_name, file_path, video_hash, duration) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (name, path, v_hash, duration))
            v_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return v_id
        except Exception as e:
            print(f"DB Error (insert_video): {e}")
            return None

    def insert_behavior_event(self, video_id, behavior_name, start, end, confidence):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Tìm behavior_id dựa trên tên (vd: 'cat_sleeping')
            cursor.execute("SELECT id FROM Behaviors WHERE behavior_name = %s", (behavior_name,))
            res = cursor.fetchone()
            
            if res:
                b_id = res[0]
                sql = """INSERT INTO BehaviorEvents (video_id, behavior_id, start_time, end_time, confidence) 
                         VALUES (%s, %s, %s, %s, %s)"""
                cursor.execute(sql, (video_id, b_id, start, end, confidence))
                conn.commit()
                print(f"MySQL: Saved behavior event {behavior_name} ({start:.1f}s -> {end:.1f}s)")
            else:
                print(f"Warning: Behavior '{behavior_name}' not found in Behaviors table")
                
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"DB Error (insert_behavior_event): {e}")

    def get_history(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT v.file_name, b.behavior_name, e.start_time, e.end_time, e.confidence 
                FROM BehaviorEvents e
                JOIN Videos v ON e.video_id = v.id
                JOIN Behaviors b ON e.behavior_id = b.id
                ORDER BY v.upload_time DESC, e.start_time ASC
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"DB Error (get_history): {e}")
            return []

    def get_all_videos(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, file_name, file_path, upload_time, duration FROM Videos ORDER BY upload_time DESC")
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"DB Error (get_all_videos): {e}")
            return []

    def get_video_events(self, video_id):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT b.behavior_name, e.start_time, e.end_time, e.confidence 
                FROM BehaviorEvents e
                JOIN Behaviors b ON e.behavior_id = b.id
                WHERE e.video_id = %s
                ORDER BY e.start_time ASC
            """
            cursor.execute(sql, (video_id,))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"DB Error (get_video_events): {e}")
            return []

    def insert_camera_session(self, session_name):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO CameraSessions (session_name, start_time, status) VALUES (%s, NOW(), 'running')"
            cursor.execute(sql, (session_name,))
            s_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return s_id
        except Exception as e:
            print(f"DB Error (insert_camera_session): {e}")
            return None

    def end_camera_session(self, session_id):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "UPDATE CameraSessions SET end_time = NOW(), status = 'completed' WHERE id = %s"
            cursor.execute(sql, (session_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"DB Error (end_camera_session): {e}")
            return False

    def insert_camera_event(self, session_id, behavior_name, start_time_dt, end_time_dt, duration, confidence):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Tìm behavior_id dựa trên tên (vd: 'cat_sleeping')
            cursor.execute("SELECT id FROM Behaviors WHERE behavior_name = %s", (behavior_name,))
            res = cursor.fetchone()
            
            if res:
                b_id = res[0]
                sql = """INSERT INTO CameraEvents (session_id, behavior_id, start_time, end_time, duration, confidence) 
                         VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (session_id, b_id, start_time_dt, end_time_dt, duration, confidence))
                conn.commit()
                print(f"MySQL: Saved camera event {behavior_name} ({start_time_dt.strftime('%H:%M:%S')} -> {end_time_dt.strftime('%H:%M:%S')}, duration: {duration:.1f}s)")
            else:
                print(f"Warning: Behavior '{behavior_name}' not found in Behaviors table")
                
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"DB Error (insert_camera_event): {e}")

    def get_all_camera_sessions(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, session_name, start_time, end_time, status FROM CameraSessions ORDER BY start_time DESC")
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"DB Error (get_all_camera_sessions): {e}")
            return []

    def get_camera_session_events(self, session_id):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT b.behavior_name, e.start_time, e.end_time, e.duration, e.confidence 
                FROM CameraEvents e
                JOIN Behaviors b ON e.behavior_id = b.id
                WHERE e.session_id = %s
                ORDER BY e.start_time ASC
            """
            cursor.execute(sql, (session_id,))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"DB Error (get_camera_session_events): {e}")
            return []

    def get_camera_behavior_stats(self, session_id):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT b.behavior_name, SUM(e.duration) as total_duration 
                FROM CameraEvents e
                JOIN Behaviors b ON e.behavior_id = b.id
                WHERE e.session_id = %s
                GROUP BY b.id
            """
            cursor.execute(sql, (session_id,))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"DB Error (get_camera_behavior_stats): {e}")
            return []
