"""Gemini AI translation engine wrapped from kakuyomu_translate.py."""

import time
from pathlib import Path
import yaml
from google import genai
from google.genai import types

THINKING_LEVEL_MAP = {
    "1": "MINIMAL",
    "2": "LOW",
    "3": "MEDIUM",
    "4": "HIGH"
}


def load_markdown(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"Missing YAML frontmatter: {path}")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid YAML frontmatter: {path}")
    metadata = yaml.safe_load(parts[1].strip()) or {}
    body = parts[2].lstrip("\r\n")

    if not isinstance(metadata, dict):
        raise ValueError("YAML frontmatter must be a valid mapping.")
    if not body.strip():
        raise ValueError("Story body content is empty.")
    return metadata, body


def build_output(metadata: dict, translation: str) -> str:
    if metadata.get("index_number") is None:
        raise ValueError("Input YAML missing 'index_number'.")
    output_metadata = {
        "title": f"Chapter {metadata['index_number']}",
        "source_url": metadata.get("source_url", ""),
    }
    yaml_text = yaml.safe_dump(output_metadata, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{yaml_text}\n---\n\n{translation.rstrip()}\n"


def run_translation(
    input_path: Path,
    output_path: Path,
    prompt_path: Path,
    api_key: str,
    model: str = "gemini-3.5-flash",
    thinking_level: str = "MEDIUM",
) -> float:
    """Translate raw Markdown using Google GenAI API."""
    if output_path.exists():
        print(f"SKIP: Output file already exists: {output_path.name}")
        return 0.0

    if not prompt_path.exists():
        raise FileNotFoundError(f"[FAILED] {prompt_path} not found.")

    system_prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not system_prompt:
        raise ValueError(f"System prompt file is empty: {prompt_path}")

    metadata, story = load_markdown(input_path)

    print(f"Input   : {input_path.name}")
    print(f"Output  : {output_path.name}")
    print(f"Model   : {model}")
    print(f"Thinking: {thinking_level}")
    print("Translating...")

    client = genai.Client(api_key=api_key)
    start_time = time.perf_counter()

    response = client.models.generate_content(
        model=model,
        contents=story,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        ),
    )

    elapsed_time = time.perf_counter() - start_time
    translation = (response.text or "").strip()

    if not translation:
        raise RuntimeError("Received empty response from Gemini API.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_output(metadata, translation), encoding="utf-8")
    print(f"Processing time: {elapsed_time:.2f} seconds")
    print(f"Done. Saved: {output_path.name}\n")

    return elapsed_time