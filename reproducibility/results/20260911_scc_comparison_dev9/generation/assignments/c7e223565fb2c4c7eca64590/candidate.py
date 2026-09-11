import re
import os
from pathlib import Path
import glob

def task_func(directory_path: str, regex_pattern: str = r'\\(.+?\\)|\\w') -> dict:
    """Extract matches from all text files in a directory."""
    if regex_pattern == r'\\(.+?\\)|\\w':
        regex_pattern = r'\(.+?\)|\w'

    pattern = re.compile(regex_pattern)
    matches_by_file = {}

    for file_path in glob.glob(os.path.join(directory_path, "*.txt")):
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        matches = []
        for match in pattern.finditer(text):
            value = match.group(0)
            if value.startswith("(") and value.endswith(")"):
                value = value[1:-1]
            matches.append(value)

        matches_by_file[os.path.basename(file_path)] = matches

    return matches_by_file