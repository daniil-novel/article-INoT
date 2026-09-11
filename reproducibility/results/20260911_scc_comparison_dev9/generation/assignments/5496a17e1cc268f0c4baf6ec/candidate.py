import subprocess
import os
import shutil
import sys

# Constants
DIRECTORY = r'c:\Program Files\VMware\VMware Server'
BACKUP_DIRECTORY = r'c:\Program Files\VMware\VMware Server\Backup'

def task_func(filename):
    source_path = os.path.join(DIRECTORY, filename)

    try:
        os.makedirs(BACKUP_DIRECTORY, exist_ok=True)
        shutil.copy2(source_path, BACKUP_DIRECTORY)
    except (OSError, shutil.Error):
        return -1

    try:
        return subprocess.call([source_path])
    except OSError:
        return -1