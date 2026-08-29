# kakuyomu-extractor
Extract contents from kakuyomu

## Cơ chế hoạt động:
1. Lấy `toc.md` với cấu trúc: `index_number. Chapter_title Link`
2. Dựa vào `index_number` trong `toc.md` để đặt tên file chapter
3. Dựa vào `Link` trong `toc.md` để parsing HTML tìm nội dung
4. Extract chapter title & content
5. Lưu về máy dưới dạng `chapter_x_raw.md`


## Tính năng:
- Tùy chỉnh range
- Extract episode → `.md`
- Output path tùy chỉnh
- Skip `.md` đã tồn tại
- Random delay giữa request
- Báo lỗi request


## Usage
### Step 1:
Đầu tiên, nhập link trang chính của truyện

```	
python kakuyomu_toc.py "Insert_URL_here" "toc.md"
```

### Step 2:
Sau đó mới bắt đầu kéo content về

**Chỉ định thư mục output:**

```
python kakuyomu_extract.py "toc.md" "chapter_cần_tải" "đường_dẫn_folder"
```

Mặc định delay giữa các request là **3–7 giây ngẫu nhiên**. Có thể tùy chỉnh:

```
python kakuyomu_extract.py "toc.md" "chapter_cần_tải" 4 8
```

→ delay ngẫu nhiên **4–8 giây**.


#### Ví dụ:

**Lấy một chapter:**

```
python kakuyomu_extract.py "toc.md" "5"
```

**Lấy một loạt:**

```
python kakuyomu_extract.py "toc.md" "5-10"
```

**Lấy nhiều episode rời nhau:**

```
python kakuyomu_extract.py "toc.md" "5,8,12"
```