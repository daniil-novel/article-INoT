import re
import os
from pathlib import Path
import glob


def task_func(directory_path: str, regex_pattern: str = r"\(.+?\)|\w") -> dict:
    directory = Path(directory_path)

    if not directory.is_dir():
        return {}

    try:
        pattern = re.compile(regex_pattern)
    except re.error:
        return {}

    results = {}

    for file_name in glob.glob(str(directory / "*.txt")):
        file_path = Path(file_name)

        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        results[file_path.name] = pattern.findall(content)

    return results
