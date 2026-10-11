from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Optional, Callable
import argparse
import hashlib
import json
import shutil
import time
import os
import re

# Assumptions
# - Modified files either change in size or modification time
# - Files are not being modified while hashing
# - At least one file exists in the target scan directory


@dataclass
class FileData:
    path: Path
    modificationTime: float

    def prettyPrint(self):
        return f"/share{str(self.path)[6:]}"


@dataclass
class HashData:
    size: int
    fileDatas: list[FileData]


def getDiskUsage():
    usage = 0
    for name in ["fast", "extra", "bulk"]:
        usage += shutil.disk_usage(f"/share/{name}").used
    return usage


# Slow
# def getFileList(root: Path = None):
#     if root is None:
#         root = Path("/share")
#     return (
#         file
#         for file in root.rglob("*")
#         if not file.is_dir() and ".zfs" not in file.parts
#     )


def getFileList(root: Path = None):
    if root is None:
        root = Path("/share")

    def _walk():
        stack: list[Path] = [root]
        while stack:
            directory = stack.pop()
            try:
                for entry in directory.iterdir():
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name != ".zfs":
                            stack.append(entry)
                    elif not entry.is_symlink():
                        yield entry
            except PermissionError as e:
                print(f"Unable to iterate directory: {str(e)}")

    return _walk()


def hashFile(file: Path):
    BUF_SIZE = 65536
    hasher = hashlib.sha3_256()

    with file.open("rb") as reader:
        while True:
            data = reader.read(BUF_SIZE)
            if not data:
                break
            hasher.update(data)

    return hasher.hexdigest()


def getHashData(
    files: Iterator[Path],
    reportProgress: Optional[Callable[[int], None]] = None,
    oldHashData: dict[str, HashData] = None,
):
    if oldHashData is None:
        oldHashData = {}

    # Convert oldHashData into a dictionary to quickly find files and their associated data
    oldFileSearchable: dict[Path, tuple[int, float, str]] = {}
    for hashStr, hashValue in oldHashData.items():
        for fileData in hashValue.fileDatas:
            oldFileSearchable[fileData.path] = (
                hashValue.size,
                fileData.modificationTime,
                hashStr,
            )

    # Get hashes for every file
    hashData: dict[str, HashData] = {}
    lastYieldTime = time.time()
    skippedFiles = 0
    skippedBytes = 0
    hashedFiles = 0
    hashedBytes = 0
    for file in files:
        # Report progress
        if reportProgress is not None:
            reportProgress(hashedBytes + skippedBytes)

        if time.time() - lastYieldTime > 600:
            # Yield every 10 minutes to write file
            yield hashData
            lastYieldTime = time.time()

        stats = file.stat()
        oldFile = oldFileSearchable.get(file)
        if (
            oldFile is not None
            and oldFile[0] == stats.st_size
            and oldFile[1] == stats.st_mtime
        ):
            # Assume file has not been changed, skip hashing, using old hash
            skippedFiles += 1
            skippedBytes += stats.st_size
            fileHash = oldFile[2]
        else:
            # Heavy call: hash the file since old file not existent or may have changed
            try:
                fileHash = hashFile(file)
            except (PermissionError, OSError) as e:
                print(f"Unable to hash file {str(file)}: {str(e)}")
                skippedFiles += 1
                skippedBytes += stats.st_size
                continue

            hashedFiles += 1
            hashedBytes += stats.st_size

        # Add file's data to hashData (new hash or append existing)
        fileData = FileData(file, stats.st_mtime)
        if fileHash in hashData:
            if hashData[fileHash].size != stats.st_size:
                print(
                    "Warning! Identical hashes differ in size! "
                    f"{hashData[fileHash]} adding {fileData} of size {stats.st_size}"
                )
            hashData[fileHash].fileDatas.append(fileData)
        else:
            hashData[fileHash] = HashData(stats.st_size, [fileData])

    hashedBytesGiga = hashedBytes / 1024.0 / 1024.0 / 1024.0
    skippedBytesGiga = skippedBytes / 1024.0 / 1024.0 / 1024.0
    print("Hashing completed")
    print(f"Hashed files: {hashedFiles} Skipped files: {skippedFiles}")
    print(
        f"Hashed bytes: {hashedBytes} ({hashedBytesGiga:.3f} gib) "
        f"Skipped bytes: {skippedBytes} ({skippedBytesGiga:.3f} gib)"
    )
    yield hashData


def writeHashData(hashData: dict[str, HashData], exportPath: Path):
    # Defaulter for Path objects for use in json dumping (how to convert Path to string)
    def pathDefaulter(obj):
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, (HashData, FileData)):
            return asdict(obj)
        raise TypeError(f"Cannot serialize {type(obj)}")

    with exportPath.open("w", encoding="utf-8") as writer:
        json.dump(hashData, writer, default=pathDefaulter)


def readHashData(importPath: Path):
    with importPath.open("r", encoding="utf-8") as reader:
        rawData = json.load(reader)

    hashData: dict[str, HashData] = {}
    for hashStr, hashValues in rawData.items():
        hashData[hashStr] = HashData(**hashValues)
        hashData[hashStr].fileDatas = [
            FileData(**fileData) for fileData in hashData[hashStr].fileDatas
        ]
        for fileData in hashData[hashStr].fileDatas:
            fileData.path = Path(fileData.path)

    return hashData


def focusSearch(focus: str, focusIsRegex: bool, searchItem: str):
    if focusIsRegex:
        return re.search(focus, searchItem) is not None

    return focus in searchItem


def getBlacklistStrings():
    blacklistPath = Path("blacklist.json")
    if not blacklistPath.exists():
        print("Notice: No blacklist.json present; considering this as empty blacklist.")
        return []

    with blacklistPath.open(mode="r", encoding="utf-8") as file:
        return json.load(file)


def filterBlacklist(fileInList: FileData, blacklistStrings: list[str]):
    for blacklistString in blacklistStrings:
        if blacklistString in str(fileInList.path):
            return False
    return True


def getAdjustedFileDatasFromBlacklist(
    blacklist: bool, blacklistStrings: list[str], fileDatas: list[FileData]
):
    if blacklist:
        return [
            fileData
            for fileData in fileDatas
            if filterBlacklist(fileData, blacklistStrings)
        ]

    return fileDatas


def runDupes(
    focus: str,
    dropSolo: bool,
    nameRestriction: str,
    printLast: bool,
    invertSort: bool,
    focusIsRegex: bool,
    blacklist: bool,
    no_zero: bool,
    hashData: dict[str, HashData],
):
    assert not (dropSolo and focus is None), "Cannot drop solo with no focus"

    blacklistStrings = getBlacklistStrings() if blacklist else []

    with open("dupesFinal.txt", "w", encoding="utf-8") as file:
        for _, hashValue in sorted(
            hashData.items(), key=lambda x: x[1].size, reverse=True
        ):
            if no_zero and hashValue.size == 0:
                continue

            adjustedFileDatas = getAdjustedFileDatasFromBlacklist(
                blacklist, blacklistStrings, hashValue.fileDatas
            )
            if len(adjustedFileDatas) <= 1:
                continue

            focusPresent = focus is None
            isSolo = True
            name = None
            nameRestrictionMet = nameRestriction != "different"
            for fileInList in adjustedFileDatas:
                if not focusPresent and focusSearch(
                    focus, focusIsRegex, str(fileInList.path)
                ):
                    focusPresent = True
                if dropSolo and not focusSearch(
                    focus, focusIsRegex, str(fileInList.path)
                ):
                    isSolo = False
                if nameRestriction is not None:
                    if name is None:
                        name = fileInList.path.name
                    else:
                        if nameRestriction == "same" and name != fileInList.path.name:
                            nameRestrictionMet = False
                        if (
                            nameRestriction == "different"
                            and name != fileInList.path.name
                        ):
                            nameRestrictionMet = True

            if nameRestrictionMet and (not dropSolo or not isSolo) and focusPresent:
                file.write(f"{hashValue.size / 1024 / 1024:.3f} mib\n")
                sortedDupes = sorted(
                    adjustedFileDatas, key=lambda x: str(x.path), reverse=invertSort
                )
                if printLast:
                    dupe = sortedDupes[-1]
                    file.write(f"{dupe.prettyPrint()}\n")
                else:
                    for dupe in sortedDupes:
                        file.write(f"{dupe.prettyPrint()}\n")
                file.write("\n")


def runHash(hashDataPath: Path, oldHashData: dict[str, HashData]):
    hashDataTempPath = Path("hashData.tmp.json")
    hashDataBakPath = Path("hashData.bak.json")

    diskUsage = getDiskUsage()
    diskUsageGb = diskUsage / 1024.0 / 1024.0 / 1024.0
    lastReport = 0

    def printProgress(bytesProgress: int):
        nonlocal lastReport
        if time.time() - lastReport > 1:
            lastReport = time.time()
            bytesProgressGib = bytesProgress / 1024.0 / 1024.0 / 1024.0
            diskPercentage = bytesProgress * 100.0 / diskUsage
            print(
                f"{bytesProgressGib:.3f} gib / {diskUsageGb:.3f} gib ({diskPercentage:.2f}%)",
                flush=True,
            )

    # Read the existing hash list, generate hashes for missing elements, and write to tmp.
    fileList = getFileList()
    for hashData in getHashData(fileList, printProgress, oldHashData):
        print("Writing hashData")
        writeHashData(hashData, hashDataTempPath)

    # Backup existing hash list, and move tmp to primary.
    hashDataBakPath.unlink(missing_ok=True)  # Windows may fail move if existing.
    if hashDataPath.exists():
        hashDataPath.rename(hashDataBakPath)
    else:
        print("No existing hashData.json, first run? Continuing finalization...")
    hashDataTempPath.rename(hashDataPath)


def runStat(blacklist: bool, hashData: dict[str, HashData]):
    fileList = getFileList()
    hashedFileCount = 0
    hashedSize = 0
    duplicateFiles = 0
    wastedSpace = 0
    blacklistedDuplicates = 0
    blacklistStrings = getBlacklistStrings() if blacklist else []
    for hashValue in hashData.values():
        adjustedFileDatas = getAdjustedFileDatasFromBlacklist(
            blacklist, blacklistStrings, hashValue.fileDatas
        )

        hashedFileCount += len(hashValue.fileDatas)
        hashedSize += hashValue.size * len(hashValue.fileDatas)
        blacklistedDuplicates += len(hashValue.fileDatas) - 1
        if len(adjustedFileDatas) > 1:
            duplicateFiles += len(adjustedFileDatas) - 1
            wastedSpace += hashValue.size * (len(adjustedFileDatas) - 1)
    totalFileCount = len(list(fileList))
    filePercentage = hashedFileCount * 100.0 / totalFileCount
    hashedSizeGb = hashedSize / 1024 / 1024 / 1024
    diskUsage = getDiskUsage()
    diskUsageGb = diskUsage / 1024 / 1024 / 1024
    diskPercentage = hashedSize * 100.0 / diskUsage
    print(f"Number of hashes: {len(hashData)}")
    print(
        "Number of hashed files vs total files: "
        f"{hashedFileCount} / {totalFileCount} ({filePercentage:.2f}%)"
    )
    print(
        "Size of hashed files vs total size: "
        f"{hashedSizeGb:.3f} gib / {diskUsageGb:.3f} gib ({diskPercentage:.2f}%)"
    )
    print(
        f"Wasted space {wastedSpace} bytes ({int((wastedSpace / 1024) / 1024)} mib, "
        f"{int(((wastedSpace / 1024) / 1024) / 1024)} gib) across {duplicateFiles} files."
    )
    if blacklist:
        print(f"Duplicate files blacklisted: {blacklistedDuplicates - duplicateFiles}")


def runFile(inputFile: Path, hashData: dict[str, HashData]):
    print("Hashing file...", end=None)
    fileHash = hashFile(inputFile)
    print("Done.")
    if fileHash in hashData:
        print("File hash found:")
        for fileData in hashData[fileHash].fileDatas:
            print(f"\t{fileData.prettyPrint()}")
    else:
        print("File hash not found.")


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w", "--wait", action="store_true", help="wait for user input before exiting"
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("hash", help="calculate hashes of all files")
    subStat = sub.add_parser("stat", help="show current dupe statistics")
    subStat.add_argument(
        "-b",
        "--blacklist",
        action="store_true",
        help="never consider blacklisted items as duplicates",
    )  # Useful for items you know are duplicates but do not want to modify (e.g. program files).

    subParse = sub.add_parser("parse", help="parse duplicate files")
    subParse.add_argument(
        "-f",
        "--focus",
        help="filter out duplicate groups that do not have this string present in at least one "
        "file path",
    )
    subParse.add_argument(
        "-d",
        "--drop-solo",
        action="store_true",
        help="filter out duplicate groups where all file paths include the focus string",
    )
    subParse.add_argument(
        "-n",
        "--name",
        choices=["same", "different"],
        help="filter out duplicate groups to retain only those where all file names are the 'same' "
        "or 'different'",
    )
    subParse.add_argument(
        "-l",
        "--last",
        action="store_true",
        help="only show the last duplicate of each group as ordered by sort()",
    )
    subParse.add_argument(
        "-i",
        "--invert",
        action="store_true",
        help="invert sort() operations (affects output and --last)",
    )
    subParse.add_argument(
        "-r",
        "--regex",
        action="store_true",
        help="treat 'focus' as a regular expression",
    )
    subParse.add_argument(
        "-b",
        "--blacklist",
        action="store_true",
        help="never consider blacklisted items as duplicates",
    )  # Useful for items you know are duplicates but do not want to modify (e.g. program files).
    subParse.add_argument(
        "-z", "--no-zero", action="store_true", help="filter out zero byte items"
    )

    subFile = sub.add_parser("file", help="identify if an input file exists somewhere")
    subFile.add_argument("inputFile")

    return parser.parse_args()


def fullRun():
    args = parseArgs()

    hashDataPath = Path("hashData.json")
    if not hashDataPath.exists():
        print("No hashData.json found, moving to known location.")
        os.chdir("/share/meta/dupes")

    if not hashDataPath.exists():
        print("Warning, no hashData found. First time?")
        hashData = {}
    else:
        print("Reading hashData...", end=None)
        hashData = readHashData(hashDataPath)
        print("Done.")

    if args.mode == "hash":
        runHash(hashDataPath, hashData)
    elif args.mode == "stat":
        runStat(args.blacklist, hashData)
    elif args.mode == "parse":
        runDupes(
            args.focus,
            args.drop_solo,
            args.name,
            args.last,
            args.invert,
            args.regex,
            args.blacklist,
            args.no_zero,
            hashData,
        )
    elif args.mode == "file":
        runFile(Path(args.inputFile), hashData)

    if args.wait:
        input("Press enter to exit...")


def main():
    # runTest()
    fullRun()


if __name__ == "__main__":
    main()
