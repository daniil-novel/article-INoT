import re
import os
from pathlib import Path
import glob


def task_func(directory_path: str, regex_pattern: str = r"\(.+?\)|\w") -> dict:
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory_path}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")

    results = {}

    for file_name in glob.glob(os.path.join(str(directory), "*.txt")):
        file_path = Path(file_name)

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        results[file_path.name] = re.findall(regex_pattern, content)

    return results
