import re
import os
from pathlib import Path
import glob


def task_func(directory_path: str, regex_pattern: str = r'\\(.+?\\)|\\w') -> dict:
    """Extract regex matches from all text files in a directory."""
    if regex_pattern == r'\\(.+?\\)|\\w':
        regex_pattern = r'\(.+?\)|\w'

    matches_by_file = {}

    for file_path in glob.glob(os.path.join(directory_path, "*.txt")):
        with open(file_path, "r", encoding="utf-8") as file:
            matches_by_file[os.path.basename(file_path)] = re.findall(
                regex_pattern, file.read()
            )

    return matches_by_file