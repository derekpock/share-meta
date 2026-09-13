from pathlib import Path
import time


class DirContext:
    def __init__(self, root: Path):
        self.path = root
        self.count = 0
        self.children = []


def writeDirCountsNonRecursive(outputFile, root: Path = None):
    excludeList: list[str] = [".zfs"]
    lastReport = 0

    if root is None:
        root = Path("/share")

    rootDirContext = DirContext(root)

    # Iterate through all directories top-down
    queue: list[DirContext] = [rootDirContext]
    for entry in queue:
        if time.time() - lastReport > 3:
            print(f"d{len(entry.path.parents)} {str(entry.path)}")
            lastReport = time.time()

        for item in entry.path.iterdir():
            entry.count += 1
            if item.is_dir() and not item.is_symlink() and not item.name in excludeList:
                # For subdirectories, they need to count their sub-items first.
                # Add to queue and keep track of the child.
                dirItem = DirContext(item)
                entry.children.append(dirItem)
                queue.append(dirItem)

    # Now in reverse order (bottom-up), sum child items into parent directory totals.
    queue.reverse()
    for entry in queue:
        for child in entry.children:
            entry.count += child.count

    queue.sort(key=lambda x: x.count)
    for entry in queue:
        outputFile.write(f"{entry.count} {str(entry.path)}\n")
        print(f"{entry.count} {str(entry.path)}")


def main():
    outputFilePath = Path("dirCountsPy.txt")
    with outputFilePath.open("w", encoding="utf-8") as outputFile:
        writeDirCountsNonRecursive(outputFile)


if __name__ == "__main__":
    main()
