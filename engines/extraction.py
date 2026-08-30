"""Chapter extraction engine wrapped from kakuyomu_extract.py."""

import random
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

from core.selection import parse_selection_string
from engines.toc import get_work_html

DEFAULT_DELAY_MIN = 3.0
DEFAULT_DELAY_MAX = 7.0

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://kakuyomu.jp/",
}


def parse_toc(toc_path: Path) -> list[dict]:
    import re
    text = toc_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^(?:(?P<idx>\d+)\.|-)\s*\[(?P<title>.+?)\]\((?P<url>https://kakuyomu\.jp/works/[^/]+/episodes/[^)]+)\)\s*$",
        re.MULTILINE,
    )
    episodes = []
    auto_index = 1

    for match in pattern.finditer(text):
        title = match.group("title").strip()
        url = match.group("url").strip()
        idx_str = match.group("idx")
        index = int(idx_str) if idx_str else auto_index

        episodes.append({
            "number": index,
            "title": title,
            "url": url,
            "filename": f"chapter_{index}_raw.md",
        })
        auto_index += 1

    if not episodes:
        raise RuntimeError("No episodes parsed from ToC file.")
    return episodes


def fetch_and_parse(session: requests.Session, episode: dict) -> tuple[str, list[str]]:
    response = session.get(episode["url"], headers=HTTP_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    title_element = soup.select_one("p.widget-episodeTitle")
    title = title_element.get_text(strip=True) if title_element else episode["title"]

    body_element = soup.select_one("div.widget-episodeBody")
    if body_element is None:
        raise RuntimeError("Could not find episode body container.")

    paragraphs = []
    for p_tag in body_element.find_all("p"):
        for br in p_tag.find_all("br"):
            br.replace_with("\n")
        clean_text = p_tag.get_text().strip()
        if clean_text:
            paragraphs.append(clean_text)

    if not paragraphs:
        raise RuntimeError("Extracted episode content is empty.")
    return title, paragraphs


def build_markdown(index_number: int, title: str, source_url: str, paragraphs: list[str]) -> str:
    body = "\n\n".join(paragraphs)
    return (
        "---\n"
        f"index_number: {index_number}\n"
        f'title: "{title.replace(chr(34), chr(92) + chr(34))}"\n'
        f'source_url: "{source_url}"\n'
        "---\n\n"
        f"# {title}\n\n"
        f"{body}\n"
    )


def run_chapter_extraction(
    toc_path: Path,
    selection_str: str,
    output_dir: Path,
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
) -> dict:
    """Extract specified chapters using polite rate limiting."""
    episodes = parse_toc(toc_path)
    available_indices = [ep["number"] for ep in episodes]
    selected_indices = set(parse_selection_string(selection_str, available_indices))
    selected_episodes = [ep for ep in episodes if ep["number"] in selected_indices]

    stats = {"success": 0, "skipped": 0, "failed": 0, "failed_list": []}

    print("\n=== CHAPTER EXTRACTION ===")

    with requests.Session() as session:
        for idx, episode in enumerate(selected_episodes, start=1):
            out_path = output_dir / episode["filename"]
            print(f"[{idx}/{len(selected_episodes)}] Chapter {episode['number']}: {episode['title']}")

            if out_path.exists():
                print(f"  -> SKIP ({out_path.name} already exists)")
                stats["skipped"] += 1
                continue

            try:
                print("  -> Fetching...")
                title, paragraphs = fetch_and_parse(session, episode)
                md = build_markdown(episode["number"], title, episode["url"], paragraphs)

                output_dir.mkdir(parents=True, exist_ok=True)
                out_path.write_text(md, encoding="utf-8")
                stats["success"] += 1
                print(f"  -> OK: {out_path.name}")
            except Exception as exc:
                stats["failed"] += 1
                stats["failed_list"].append(episode["number"])
                print(f"  -> FAILED: {exc}")

            if idx < len(selected_episodes):
                delay = random.uniform(delay_min, delay_max)
                print(f"  -> Waiting {delay:.1f}s...")
                time.sleep(delay)

    return stats