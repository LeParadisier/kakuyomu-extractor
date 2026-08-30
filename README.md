## Requirements

1. Python 3.9+
2. Cài đặt dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Nếu dùng AI, phải chuẩn bị API KEY

## Khởi chạy

1. Mở Powershell
2. Chạy lệnh

    ```
    python app.py
    ```

3. Làm theo hướng dẫn

## Chú thích:

- Định dạng chọn chương: 
    Hỗ trợ chuỗi đơn (1), khoảng (1-10), phân tách bằng dấu phẩy (1,3,7), hoặc kết hợp (1,3,7-10).

- Tính năng Resume (Work-in-process)
    Tự động bỏ qua các file đã tồn tại

## To-do list
- Cơ chế tùy chọn System prompt
- Check dependency chỉ cần 1 lần vào lần đầu launch?
- Cơ chế check file `toc.md` có phù hợp không?
- Lần 1 chạy thì xuất `toc.md`
- Nhưng lần 2 trở đi thì đâu cần phải xuất toc.md ra nữa? chỉ việc dựa vào `toc.md` để tiếp tục tiến trình? 
- Logic dịch file hàng loạt bằng AI? 
- Số lượng token đã dùng?