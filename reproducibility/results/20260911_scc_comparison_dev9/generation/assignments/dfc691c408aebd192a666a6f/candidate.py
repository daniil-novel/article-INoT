import subprocess
import os
import shutil
import sys

# Constants
DIRECTORY = 'c:\Program Files\VMware\VMware Server'
BACKUP_DIRECTORY = 'c:\Program Files\VMware\VMware Server\Backup'


def task_func(filename):
    source_path = os.path.join(DIRECTORY, filename)
    backup_path = os.path.join(BACKUP_DIRECTORY, filename)

    try:
        shutil.copy2(source_path, backup_path)
    except (OSError, shutil.Error):
        return -1

    try:
        return subprocess.call([source_path])
    except OSError:
        return -1