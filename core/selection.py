"""Parser utility for user-selected chapter ranges."""

import re


def parse_selection_string(selection: str, available_numbers: list[int]) -> list[int]:
    """Parse selection patterns like '1', '1-10', '1,3,7' into a validated list of indices."""
    available_set = set(available_numbers)
    selected = set()

    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue

        if re.fullmatch(r"\d+", part):
            selected.add(int(part))
            continue

        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start > end:
                start, end = end, start
            selected.update(range(start, end + 1))
            continue

        raise ValueError(f"Invalid selection format: '{part}'. Use formats like 1, 1-10, or 1,3,7.")

    invalid_indices = sorted(selected - available_set)
    if invalid_indices:
        raise ValueError(f"Selected index(es) non-existent or out of range: {invalid_indices}")

    return sorted(selected)