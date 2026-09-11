import subprocess
import os
import shutil
import sys

# Constants
DIRECTORY = 'c:\\Program Files\\VMware\\VMware Server'
BACKUP_DIRECTORY = 'c:\\Program Files\\VMware\\VMware Server\\Backup'


def task_func(filename):
    try:
        source_path = os.path.join(DIRECTORY, filename)
        destination_path = os.path.join(BACKUP_DIRECTORY, filename)

        if not os.path.isfile(source_path):
            return -1

        os.makedirs(BACKUP_DIRECTORY, exist_ok=True)
        shutil.copy2(source_path, destination_path)

        completed_process = subprocess.run(
            [destination_path],
            check=False
        )
        return int(completed_process.returncode)
    except Exception:
        return -1
