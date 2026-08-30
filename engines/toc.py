"""Table of Contents extraction engine wrapped from kakuyomu_toc.py."""

import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://kakuyomu.jp"


def get_work_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def extract_next_data(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if script is None:
        raise RuntimeError("Failed to locate __NEXT_DATA__ element.")
    return json.loads(script.string)


def resolve_ref(ref, apollo):
    if isinstance(ref, dict) and "__ref" in ref:
        return apollo.get(ref["__ref"])
    return ref


def extract_toc(data: dict):
    page_props = data["props"]["pageProps"]
    apollo = page_props["__APOLLO_STATE__"]
    work_id = data["query"]["workId"]
    work_key = f"Work:{work_id}"

    if work_key not in apollo:
        raise RuntimeError(f"Key {work_key} not found in Apollo state.")

    work = apollo[work_key]
    toc_refs = work.get("tableOfContentsV2")

    if not toc_refs:
        raise RuntimeError("Missing tableOfContentsV2 structure.")

    result = []
    chapter_count = 0
    episode_count = 0

    for chapter_ref in toc_refs:
        chapter = resolve_ref(chapter_ref, apollo)
        if not chapter:
            continue

        chapter_title = chapter.get("title", "").strip()
        if chapter_title:
            chapter_count += 1
            result.append({"type": "chapter", "index": chapter_count, "title": chapter_title})

        episode_unions = chapter.get("episodeUnions", [])
        for union_ref in episode_unions:
            union = resolve_ref(union_ref, apollo)
            if not union:
                continue

            episode = None
            if union.get("__typename") == "Episode":
                episode = union
            elif "episode" in union:
                episode = resolve_ref(union["episode"], apollo)
            elif "episodeRef" in union:
                episode = resolve_ref(union["episodeRef"], apollo)

            if episode is None:
                for value in union.values():
                    if isinstance(value, dict) and "__ref" in value:
                        candidate = resolve_ref(value, apollo)
                        if isinstance(candidate, dict) and candidate.get("__typename") == "Episode":
                            episode = candidate
                            break

            if not episode:
                continue

            episode_id = episode.get("id")
            episode_title = episode.get("title", "").strip()

            if not episode_id or not episode_title:
                continue

            episode_count += 1
            result.append({
                "type": "episode",
                "index": episode_count,
                "title": episode_title,
                "url": f"{BASE_URL}/works/{work_id}/episodes/{episode_id}",
            })

    return result, work


def build_markdown(toc: list, work: dict) -> str:
    work_title = work.get("title", "Kakuyomu Work").strip()
    lines = [f"# {work_title}", ""]

    for item in toc:
        if item["type"] == "chapter":
            lines.append(f"## Chương {item['index']}: {item['title']}")
            lines.append("")
        elif item["type"] == "episode":
            lines.append(f"{item['index']}. [{item['title']}]({item['url']})")

    return "\n".join(lines) + "\n"


def run_toc_extraction(url: str, output_path: Path) -> dict:
    """Execute ToC extraction pipeline."""
    html = get_work_html(url)
    data = extract_next_data(html)
    toc, work = extract_toc(data)

    if not toc:
        raise RuntimeError("Empty ToC output generated.")

    markdown = build_markdown(toc, work)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    chapter_count = sum(item["type"] == "chapter" for item in toc)
    episode_count = sum(item["type"] == "episode" for item in toc)

    return {"chapters": chapter_count, "episodes": episode_count}