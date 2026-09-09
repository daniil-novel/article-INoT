import subprocess
import os
import shutil
import sys

# Constants
DIRECTORY = r"c:\Program Files\VMware\VMware Server"
BACKUP_DIRECTORY = r"c:\Program Files\VMware\VMware Server\Backup"


def task_func(filename):
    try:
        if not isinstance(filename, str) or not filename:
            return -1

        source_path = os.path.abspath(os.path.join(DIRECTORY, filename))
        backup_root = os.path.abspath(BACKUP_DIRECTORY)

        if os.path.commonpath((source_path, os.path.abspath(DIRECTORY))) != os.path.abspath(DIRECTORY):
            return -1

        if os.path.commonpath((backup_root, os.path.abspath(DIRECTORY))) != os.path.abspath(DIRECTORY):
            return -1

        if not os.path.isfile(source_path):
            return -1

        relative_path = os.path.relpath(source_path, os.path.abspath(DIRECTORY))
        backup_path = os.path.abspath(os.path.join(backup_root, relative_path))

        if os.path.commonpath((backup_path, backup_root)) != backup_root:
            return -1

        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(source_path, backup_path)

        return subprocess.run([backup_path], check=False).returncode
    except (OSError, shutil.Error, subprocess.SubprocessError, ValueError):
        return -1
