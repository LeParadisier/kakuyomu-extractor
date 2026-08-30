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
DEFAULT_PROMPT_SRC = APP_DIR / "prompts" / "default.txt"


def get_user_choice(prompt: str, valid_choices: list[str]) -> str:
    while True:
        choice = input(prompt).strip().upper()
        if choice in valid_choices:
            return choice
        print(f"Invalid option. Select one of: {', '.join(valid_choices)}")


def main():
    print("==========================================")
    print("  Kakuyomu Novel Auto-Translator System   ")
    print("==========================================")

    # 1. Ask whether to use AI
    ai_choice = get_user_choice("Do you want to use AI translation? [Y/N]: ", ["Y", "N"])
    enable_ai = (ai_choice == "Y")

    # 2. Pre-flight Check
    if not run_preflight_check(enable_ai):
        print("\nPre-flight check failed. Exiting.")
        sys.exit(1)

    # 3. API Key Acquisition (if AI enabled)
    api_key = ""
    if enable_ai:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            api_key = input("\nEnter GEMINI_API_KEY: ").strip()
            if not api_key:
                print("API Key is required for AI translation. Exiting.")
                sys.exit(1)

    # 4. Project Folder Selection & Initialization
    proj_input = input("\nProject folder path: ").strip()
    if not proj_input:
        print("Project folder cannot be empty.")
        sys.exit(1)

    project_dir = initialize_project_folders(Path(proj_input), enable_ai, DEFAULT_PROMPT_SRC)
    print(f"[OK] Project directory setup at: {project_dir}")

    # 5. Kakuyomu URL & ToC Extraction
    url = input("\nKakuyomu work URL:\n> ").strip()
    if "kakuyomu.jp/works/" not in url:
        print("[FAILED] Invalid Kakuyomu work URL format.")
        sys.exit(1)

    toc_file = project_dir / "toc" / "toc.md"
    print("\n=== TOC EXTRACTION ===")
    print("Downloading work page...")
    try:
        toc_stats = run_toc_extraction(url, toc_file)
        print("[OK] ToC extraction completed.")
        print(f"Output   : toc/toc.md")
        print(f"Chapters : {toc_stats['chapters']}")
        print(f"Episodes : {toc_stats['episodes']}")
    except Exception as exc:
        print(f"[FAILED] ToC extraction failed: {exc}")
        sys.exit(1)

    # 6. Chapter Extraction Selection
    print("\nHow many chapters do you want to download?")
    print("Examples: 1 | 1-10 | 1,3,7 | 1,3,7-10")
    extract_selection = input("Selection:\n> ").strip()

    raw_dir = project_dir / "raw"
    extract_stats = run_chapter_extraction(toc_file, extract_selection, raw_dir)

    print("\n=== EXTRACTION COMPLETE ===")
    print(f"Success : {extract_stats['success']}")
    print(f"Skipped : {extract_stats['skipped']}")
    print(f"Failed  : {extract_stats['failed']}")
    if extract_stats["failed_list"]:
        print(f"Failed chapter numbers: {extract_stats['failed_list']}")

    # Stop here if AI disabled
    if not enable_ai:
        print("\nApplication finished.")
        return

    # 7. AI Translation Setup & Execution
    print("\n=== AI TRANSLATION CONFIGURATION ===")
    available_raws = sorted([
        int(f.name.split("_")[1]) for f in raw_dir.glob("chapter_*_raw.md")
    ])

    if not available_raws:
        print("[FAILED] No raw chapter files available for translation.")
        sys.exit(1)

    print(f"Available raw chapters: {available_raws}")
    trans_selection = input("Select chapters to translate:\n> ").strip()

    try:
        target_indices = parse_selection_string(trans_selection, available_raws)
    except ValueError as err:
        print(f"[FAILED] {err}")
        sys.exit(1)

    # Config parameters
    model = "gemini-3.5-flash"
    print("\nSelect Thinking Level:")
    print("1. MINIMAL\n2. LOW\n3. MEDIUM\n4. HIGH")
    lvl_choice = get_user_choice("Choice [1-4]: ", ["1", "2", "3", "4"])
    thinking_level = THINKING_LEVEL_MAP[lvl_choice]

    prompt_file = project_dir / "system_prompt" / "default.txt"
    ai_dir = project_dir / "AI_translated"

    print("\n=== STARTING TRANSLATION ===")
    translated_count = 0
    failed_count = 0

    for ch_num in target_indices:
        input_path = raw_dir / f"chapter_{ch_num}_raw.md"
        output_path = ai_dir / f"chapter_{ch_num}_ai.md"

        if not input_path.exists():
            print(f"[SKIP] Raw file missing: {input_path.name}")
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
            translated_count += 1
        except Exception as exc:
            print(f"[ERROR] Translating chapter {ch_num} failed: {exc}")
            failed_count += 1

    print("=== TRANSLATION COMPLETE ===")
    print(f"Processed : {translated_count}")
    print(f"Errors    : {failed_count}")
    print("Application finished.")


if __name__ == "__main__":
    main()