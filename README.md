Command-line tương tác qua Powershell/Terminal windows để trích xuất content trên kakuyomu
Có hỗ trợ tích hợp AI

---

## Requirements

1. Python 3.9+
2. Cài đặt dependencies:
   
   ```
   pip install -r requirements.txt
   ```
3. Nếu dùng AI, phải chuẩn bị API KEY

## Usage
1. Download file zip và giải nén
2. Mở Powershell trong thư mục giải nén
3. Chạy lệnh

    ```
    python app.py
    ```


## To-do
1. Cần có cơ chế thay đổi model AI
    Hiện tại mặc định là gemini-3.5-flash
2. Tối ưu hóa logic của hệ thống `engine/`

## Update logs

### 07/Sep/2026
Overhaul 90% cách tương tác 
Hoàn thiện logic
