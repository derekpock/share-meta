# (broken/untested) Compare file lists from backup and share folders, showing which files are new/old/moved/etc.

import sys
import hashlib
from tqdm import tqdm
from pathlib import Path

# BUF_SIZE is totally arbitrary, change for your app!
BUF_SIZE = 65536  # lets read stuff in 64kb chunks!


def hashFile(path: str):
    md5 = hashlib.md5()
    # sha1 = hashlib.sha1()

    with open(path.strip(), "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
            # sha1.update(data)

    return md5.hexdigest()
    # print("MD5: {0}".format(md5.hexdigest()))
    # print("SHA1: {0}".format(sha1.hexdigest()))


def sizeFile(path: str):
    return Path(path.strip()).stat().st_size


def customHash(path: str):
    return f"{Path(path.strip()).name}{sizeFile(path)}"


def writeFile(path, keys: list[str], myList):
    with open(path, "w", encoding="utf-8") as file:
        for key in keys:
            file.write(f"{myList[key][0].strip()}\n")


with open("backupFileList.txt", "r", encoding="utf-8") as file:
    oldLines = file.readlines()

with open("shareFileList.txt", "r", encoding="utf-8") as file:
    newLines = file.readlines()

oldLinesData = {}
for line in tqdm(oldLines):
    oldLinesData[line] = (False,)

newLinesData = {}
for line in tqdm(newLines):
    newLinesData[line] = (False,)

removedLines = {}
removedFileNames = {}
for line in tqdm(oldLines):
    if not line in newLinesData:
        removedFileNames[Path(line.strip()).name] = False
        myHash = customHash(f"/backup/{line[2:]}")
        if myHash in removedLines:
            removedLines[myHash] = (line, removedLines[myHash][1] + 1)
        else:
            removedLines[myHash] = (line, 1)

addedLines = {}
addedFileNames = {}
for line in tqdm(newLines):
    if not line in oldLinesData:
        addedFileNames[Path(line.strip()).name] = False
        myHash = customHash(f"/share/{line[2:]}")
        if myHash in addedLines:
            addedLines[myHash] = (line, addedLines[myHash][1] + 1)
        else:
            addedLines[myHash] = (line, 1)

abandonedRemoveLines = []
maybeAbandonedRemoveLines = []
for key in tqdm(removedLines.keys()):
    if not key in addedLines:
        if not Path(removedLines[key][0].strip()).name in addedFileNames:
            abandonedRemoveLines.append(key)
        else:
            maybeAbandonedRemoveLines.append(key)

newAddedLines = []
maybeNewAddedLines = []
for key in tqdm(addedLines.keys()):
    if not key in removedLines:
        if not Path(addedLines[key][0].strip()).name in removedFileNames:
            newAddedLines.append(key)
        else:
            maybeNewAddedLines.append(key)

print(f"Abandoned {len(abandonedRemoveLines)}")
print(f"Maybe abandoned {len(maybeAbandonedRemoveLines)}")
print(f"Created {len(newAddedLines)}")
print(f"Maybe created {len(maybeNewAddedLines)}")

writeFile("rsyncSub/abandoned.txt", abandonedRemoveLines, removedLines)
writeFile("rsyncSub/maybeAbandoned.txt", maybeAbandonedRemoveLines, removedLines)
writeFile("rsyncSub/created.txt", newAddedLines, addedLines)
writeFile("rsyncSub/maybeCreated.txt", maybeNewAddedLines, addedLines)
