"""FileChanged.py

Utility functions for checking for file changes.

"""

import hashlib
import os


def fileMD5(filename):
    hashMD5 = hashlib.md5()
    with open(filename, "rb") as fileHandle:
        for chunk in iter(lambda: fileHandle.read(4096), b""):
            hashMD5.update(chunk)
    return hashMD5.hexdigest()


def fileTime(filename):
    return round(os.stat(filename).st_mtime)


def fileStats(filename):
    return (fileTime(filename), fileMD5(filename))


def fileTimeChanged(filename, oldFileTime):
    checkFileTIme = fileTime(filename)
    if checkFileTIme != oldFileTime:
        return True
    else:
        return False


def fileContentChanged(filename, oldFileMD5):
    checkFileMD5 = fileMD5(filename)
    if checkFileMD5 != oldFileMD5:
        return True
    else:
        return False


def fileChanged(filename, oldFileTime, oldFileMD5):
    return fileContentChanged(filename, oldFileMD5) or fileTimeChanged(
        filename, oldFileTime
    )
