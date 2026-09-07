"""Main Interactive Terminal Application Orchestrator."""

import os
import sys
from pathlib import Path

from core.preflight import run_preflight_check
from core.project import initialize_project_folders
from core.selection import parse_selection_string
from engines.toc import run_toc_extraction
from engines.extraction import run_chapter_extraction
from engines.translation import THINKING_LEVEL_MAP, run_translation

APP_DIR = Path(__file__).parent.resolve()
PROJECTS_BASE_DIR = APP_DIR / "Projects"
DEFAULT_PROMPT_SRC = APP_DIR / "prompts" / "default.txt"


def get_user_choice(prompt: str, valid_choices: list[str]) -> str:
    while True:
        choice = input(prompt).strip().upper()
        if choice in valid_choices:
            return choice
        print(f"Lựa chọn không hợp lệ. Vui lòng chọn: {', '.join(valid_choices)}")


def extract_chapters_flow(project_dir: Path):
    """Xử lý luồng trích xuất chapter từ internet."""
    toc_file = project_dir / "toc" / "toc.md"
    raw_dir = project_dir / "raw"

    if not toc_file.exists():
        print("\n[LỖI] Không tìm thấy file toc.md trong project. Vui lòng trích xuất ToC trước.")
        return

    print("\nNhập danh sách chapter muốn trích xuất (Ví dụ: 1 | 1-10 | 1,3,7 | 1,3,7-10 | Nhập 0 để hủy)):")
    extract_selection = input("> ").strip()

    if extract_selection == "0":
        print("[THÔNG BÁO] Đã hủy trích xuất chapter.")
        return

    print("\n=== ĐANG TRÍCH XUẤT CHAPTER ===")
    extract_stats = run_chapter_extraction(toc_file, extract_selection, raw_dir)
    
    print("\n=== KẾT QUẢ TRÍCH XUẤT ===")
    print(f"- Thành công : {extract_stats['success']}")
    print(f"- Bỏ qua     : {extract_stats['skipped']}")
    print(f"- Thất bại   : {extract_stats['failed']}")
    if extract_stats["failed_list"]:
        print(f"- Các chapter thất bại: {extract_stats['failed_list']}")


def translate_chapters_flow(project_dir: Path, api_key: str, enable_ai: bool):
    """Xử lý luồng chuyển chapter lên AI dịch và retry nếu thất bại."""
    if not enable_ai or not api_key:
        print("\n[CẢNH BÁO] Tính năng dịch AI đang bị tắt hoặc thiếu API Key.")
        return

    raw_dir = project_dir / "raw"
    ai_dir = project_dir / "AI_translated"
    prompt_file = project_dir / "system_prompt" / "default.txt"

    available_raws = sorted([
        int(f.name.split("_")[1]) for f in raw_dir.glob("chapter_*_raw.md")
    ])

    if not available_raws:
        print("\n[LỖI] Chưa có chapter raw nào trong thư mục raw/ để dịch.")
        return

    print(f"\nDanh sách chapter raw hiện có: {available_raws}")
    trans_selection = input("Chọn chapter cần dịch (Ví dụ: 1 | 1-5 | 1,3,7 | Nhập 0 để hủy):\n> ").strip()

    if trans_selection == "0":
        print("[THÔNG BÁO] Đã hủy dịch AI.")
        return

    try:
        target_indices = parse_selection_string(trans_selection, available_raws)
    except ValueError as err:
        print(f"[LỖI] {err}")
        return

    model = "gemini-3.5-flash"
    print("\nChọn Thinking Level:")
    print("1. MINIMAL\n2. LOW\n3. MEDIUM\n4. HIGH")
    lvl_choice = get_user_choice("Lựa chọn [1-4]: ", ["1", "2", "3", "4"])
    thinking_level = THINKING_LEVEL_MAP[lvl_choice]

    current_targets = list(target_indices)

    # Vòng lặp dịch & xử lý Retry
    while current_targets:
        print(f"\n=== ĐANG TIẾN HÀNH DỊCH AI ({len(current_targets)} chapter) ===")
        translated_count = 0
        failed_list = []

        for ch_num in current_targets:
            input_path = raw_dir / f"chapter_{ch_num}_raw.md"
            output_path = ai_dir / f"chapter_{ch_num}_ai.md"

            if not input_path.exists():
                print(f"[SKIP] Thiếu tệp raw: {input_path.name}")
                failed_list.append(ch_num)
                continue

            try:
                run_translation(
                    input_path=input_path,
                    output_path=output_path,
                    prompt_path=prompt_file,
                    api_key=api_key,
                    model=model,
                    thinking_level=thinking_level,
                )
                print(f"[OK] Đã dịch chapter {ch_num}")
                translated_count += 1
            except Exception as exc:
                print(f"[LỖI] Dịch chapter {ch_num} thất bại: {exc}")
                failed_list.append(ch_num)

        # Báo cáo kết quả tổng hợp
        print("\n=== KẾT QUẢ DỊCH AI ===")
        print(f"- Pass   : {translated_count}")
        print(f"- Failed : {len(failed_list)}")

        if failed_list:
            print(f"- Danh sách chapter bị lỗi: {failed_list}")
            retry = get_user_choice("\nBạn có muốn retry các chapter thất bại không? [Y/N]: ", ["Y", "N"])
            if retry == "Y":
                current_targets = failed_list
                continue

        break


def create_new_project_flow(enable_ai: bool, api_key: str):
    """Tạo mới project và chạy quy trình mặc định (ToC -> Chapter -> AI)."""
    print("\n=== CREATE NEW PROJECT ===")
    proj_name = input("Nhập tên project: ").strip()
    if not proj_name:
        print("[LỖI] Tên project không được để trống.")
        return

    project_dir = PROJECTS_BASE_DIR / proj_name
    project_dir = initialize_project_folders(project_dir, enable_ai, DEFAULT_PROMPT_SRC)
    print(f"[OK] Khởi tạo thành công thư mục project tại: {project_dir}")

    # 1. Trích xuất ToC
    url = input("\nNhập Kakuyomu work URL:\n> ").strip()
    if "kakuyomu.jp/works/" not in url:
        print("[LỖI] URL Kakuyomu không hợp lệ.")
        return

    toc_file = project_dir / "toc" / "toc.md"
    print("\n=== TRÍCH XUẤT TOC ===")
    try:
        toc_stats = run_toc_extraction(url, toc_file)
        print("[OK] Trích xuất ToC hoàn tất.")
        print(f"- File đầu ra : toc/toc.md")
        print(f"- Chapters    : {toc_stats['chapters']}")
        print(f"- Episodes    : {toc_stats['episodes']}")
    except Exception as exc:
        print(f"[LỖI] Trích xuất ToC thất bại: {exc}")
        return

    # 2. Trích xuất Chapter
    extract_chapters_flow(project_dir)

    # 3. Hỏi dịch AI
    if enable_ai:
        do_trans = get_user_choice("\nBạn có muốn dịch AI các chapter vừa tải không? [Y/N] (Bấm 0 để quay lại): ", ["Y", "N", "0"])
        if do_trans == "Y":
            translate_chapters_flow(project_dir, api_key, enable_ai)
        else:
            print("[THÔNG BÁO] Bỏ qua bước dịch AI.")
            return

def view_existing_projects_flow(enable_ai: bool, api_key: str):
    """Hiển thị các project hiện có, quét báo cáo và xử lý các hành động kế tiếp."""
    if not PROJECTS_BASE_DIR.exists():
        PROJECTS_BASE_DIR.mkdir(parents=True, exist_ok=True)

    project_folders = [p for p in PROJECTS_BASE_DIR.iterdir() if p.is_dir()]

    if not project_folders:
        print("\nHiện chưa có project nào trong thư mục Projects/.")
        return

    print("\n=== DANH SÁCH PROJECTS ===")
    for idx, p in enumerate(project_folders, 1):
        print(f"{idx}. {p.name}")

    choice_idx = input("\nChọn project muốn xem (nhập số, hoặc bấm 0 để quay lại): ").strip()

    if choice_idx == "0":
        return
    
    if not choice_idx.isdigit() or not (1 <= int(choice_idx) <= len(project_folders)):
        print("[LỖI] Lựa chọn không hợp lệ.")
        return

    selected_proj = project_folders[int(choice_idx) - 1]

    # Quét folder và lặp lại menu sau mỗi thao tác
    while True:
        toc_file = selected_proj / "toc" / "toc.md"
        raw_files = sorted(list((selected_proj / "raw").glob("chapter_*_raw.md")))
        ai_files = sorted(list((selected_proj / "AI_translated").glob("chapter_*_ai.md")))
        prompt_file = selected_proj / "system_prompt" / "default.txt"

        print(f"\n==========================================")
        print(f" BÁO CÁO TRẠNG THÁI: {selected_proj.name}")
        print(f"==========================================")
        print(f"- Tệp toc.md        : {'Có' if toc_file.exists() else 'Chưa có'}")
        print(f"- Chapter raw đã có : {len(raw_files)} file")
        print(f"- Chapter AI đã dịch: {len(ai_files)} file")
        print(f"- Tệp system_prompt : {'Có' if prompt_file.exists() else 'Chưa có'}")
        print(f"==========================================")

        print("\nBạn muốn làm gì kế tiếp?")
        print("1. Trích xuất chapter")
        print("2. Chuyển chapter lên AI dịch")
        print("3. Quay lại danh sách Project")

        sub_choice = get_user_choice("Chọn [1-3]: ", ["1", "2", "3"])

        if sub_choice == "1":
            extract_chapters_flow(selected_proj)
            # Quay lại bước 3 (báo cáo trạng thái)
        elif sub_choice == "2":
            translate_chapters_flow(selected_proj, api_key, enable_ai)
            # Quay lại bước 3 (báo cáo trạng thái)
        elif sub_choice == "3":
            break


def main():
    print("==========================================")
    print("  Kakuyomu Novel Auto-Translator System   ")
    print("==========================================")

    # 1. Hỏi dùng AI translate
    ai_choice = get_user_choice("Do you want to use AI translation? [Y/N]: ", ["Y", "N"])
    enable_ai = (ai_choice == "Y")

    # 2. Check môi trường & dependencies
    print("\nChecking environment & dependencies...")
    if not run_preflight_check(enable_ai):
        print("\nPre-flight check failed. Exiting.")
        sys.exit(1)

    # 3. Check API Key nếu có dùng AI
    api_key = ""
    if enable_ai:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            api_key = input("\nEnter GEMINI_API_KEY: ").strip()
            if not api_key:
                print("API Key is required for AI translation. Exiting.")
                sys.exit(1)

    # Menu chính: Projects
    while True:
        print("\n==========================================")
        print("                PROJECTS                  ")
        print("==========================================")
        print("1. Create new project")
        print("2. View existed projects")
        print("3. Exit")

        proj_choice = get_user_choice("Select option [1-3]: ", ["1", "2", "3"])

        if proj_choice == "1":
            create_new_project_flow(enable_ai, api_key)
        elif proj_choice == "2":
            view_existing_projects_flow(enable_ai, api_key)
        elif proj_choice == "3":
            print("\nExiting application.")
            sys.exit(0)


if __name__ == "__main__":
    main()