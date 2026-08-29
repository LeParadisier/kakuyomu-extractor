import re
import random
import time
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =========================
# Configuration
# =========================

DEFAULT_DELAY_MIN = 3.0
DEFAULT_DELAY_MAX = 7.0

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://kakuyomu.jp/",
}


def parse_toc(toc_path: Path) -> list[dict]:
    """Extract episode index, title, and URL from a Markdown ToC."""
    text = toc_path.read_text(encoding="utf-8")

    # Match both "1. [Title](URL)" and "- [Title](URL)"
    pattern = re.compile(
        r"^(?:(?P<idx>\d+)\.|-)\s*\[(?P<title>.+?)\]\((?P<url>https://kakuyomu\.jp/works/"
        r"[^/]+/episodes/[^)]+)\)\s*$",
        re.MULTILINE,
    )

    episodes = []
    auto_index = 1

    for match in pattern.finditer(text):
        title = match.group("title").strip()
        url = match.group("url").strip()
        idx_str = match.group("idx")

        if idx_str:
            index = int(idx_str)
        else:
            index = auto_index

        filename = f"chapter_{index}_raw.md"

        episodes.append(
            {
                "number": index,
                "title": title,
                "url": url,
                "filename": filename,
            }
        )
        auto_index += 1

    if not episodes:
        raise RuntimeError("Không tìm thấy episode nào trong ToC.")

    return episodes


def parse_selection(selection: str, episodes: list[dict]) -> list[dict]:
    """Parse selections such as 5, 5-10, 5,8,12 based on episode index."""
    by_number = {
        episode["number"]: episode
        for episode in episodes
        if episode["number"] is not None
    }

    selected_numbers = set()

    for part in selection.split(","):
        part = part.strip()

        if not part:
            continue

        if re.fullmatch(r"\d+", part):
            selected_numbers.add(int(part))
            continue

        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))

            if start > end:
                start, end = end, start

            selected_numbers.update(range(start, end + 1))
            continue

        raise ValueError(
            f"Selection không hợp lệ: '{part}'. "
            "Dùng dạng 5, 5-10 hoặc 5,8,12."
        )

    missing = sorted(n for n in selected_numbers if n not in by_number)

    if missing:
        raise ValueError(
            "Không tìm thấy episode chỉ số: "
            + ", ".join(map(str, missing))
        )

    return [
        by_number[number]
        for number in sorted(selected_numbers)
    ]


def fetch_and_parse(
    session: requests.Session,
    episode: dict,
) -> tuple[str, list[str]]:
    """Fetch and parse an episode entirely in memory."""
    response = session.get(
        episode["url"],
        headers=HTTP_HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    title_element = soup.select_one("p.widget-episodeTitle")

    if title_element:
        title = title_element.get_text(strip=True)
    else:
        title = episode["title"]

    body_element = soup.select_one("div.widget-episodeBody")

    if body_element is None:
        raise RuntimeError("Không tìm thấy widget-episodeBody.")

    paragraphs = []

    for p_tag in body_element.find_all("p"):
        for br in p_tag.find_all("br"):
            br.replace_with("\n")

        clean_text = p_tag.get_text().strip()

        if clean_text:
            paragraphs.append(clean_text)

    if not paragraphs:
        raise RuntimeError("Episode body rỗng.")

    return title, paragraphs


def build_markdown(title: str, source_url: str, paragraphs: list[str]) -> str:
    """Build an Obsidian-compatible Markdown note."""
    body = "\n\n".join(paragraphs)

    return (
        "---\n"
        f'title: "{title.replace(chr(34), chr(92) + chr(34))}"\n'
        f'source_url: "{source_url}"\n'
        "---\n\n"
        f"# {title}\n\n"
        f"{body}\n"
    )


def save_markdown(output_dir: Path, filename: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / filename
    path.write_text(content, encoding="utf-8")

    return path


def main():
    if len(sys.argv) < 3:
        print(
            'Usage: python kakuyomu_extract.py "<toc.md>" "<selection>" '
            '[output_dir] [delay_min] [delay_max]'
        )
        print()
        print("Examples:")
        print('  python kakuyomu_extract.py "toc.md" "1"')
        print('  python kakuyomu_extract.py "toc.md" "1-10"')
        print('  python kakuyomu_extract.py "toc.md" "1,5,10"')
        print(
            '  python kakuyomu_extract.py "toc.md" "1-20" '
            '"episodes" 4 8'
        )
        sys.exit(1)

    toc_path = Path(sys.argv[1])

    if not toc_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy ToC: {toc_path}")

    selection = sys.argv[2]
    output_dir = (
        Path(sys.argv[3])
        if len(sys.argv) >= 4
        else toc_path.parent
    )

    delay_min = (
        float(sys.argv[4])
        if len(sys.argv) >= 5
        else DEFAULT_DELAY_MIN
    )
    delay_max = (
        float(sys.argv[5])
        if len(sys.argv) >= 6
        else DEFAULT_DELAY_MAX
    )

    if delay_min < 0 or delay_max < delay_min:
        raise ValueError("Khoảng delay không hợp lệ.")

    episodes = parse_toc(toc_path)
    selected = parse_selection(selection, episodes)

    print("=== KAKUYOMU EPISODE EXTRACTOR ===")
    print(f"ToC       : {toc_path}")
    print(f"Selected  : {len(selected)} episode(s)")
    print(f"Output    : {output_dir}")
    print(f"Delay     : {delay_min:g}-{delay_max:g} seconds")
    print()

    stats = {
        "success": 0,
        "skipped": 0,
        "failed": 0,
    }

    with requests.Session() as session:
        for index, episode in enumerate(selected, start=1):
            output_path = output_dir / episode["filename"]

            print(
                f"[{index}/{len(selected)}] "
                f"Chapter {episode['number']}: {episode['title']}"
            )

            if output_path.exists():
                print(f"  -> SKIP ({output_path.name} đã tồn tại)")
                stats["skipped"] += 1
                continue

            try:
                print("  -> Fetching...")

                title, paragraphs = fetch_and_parse(
                    session,
                    episode,
                )

                markdown = build_markdown(
                    title,
                    episode["url"],
                    paragraphs,
                )

                save_markdown(
                    output_dir,
                    episode["filename"],
                    markdown,
                )

                stats["success"] += 1
                print(f"  -> OK: {output_path.name}")

            except Exception as exc:
                stats["failed"] += 1
                print(f"  -> FAILED: {exc}")

            if index < len(selected):
                delay = random.uniform(delay_min, delay_max)
                print(f"  -> Waiting {delay:.1f}s...")
                time.sleep(delay)

    print()
    print("=== COMPLETE ===")
    print(f"Extracted : {stats['success']}")
    print(f"Skipped   : {stats['skipped']}")
    print(f"Failed    : {stats['failed']}")


if __name__ == "__main__":
    main()