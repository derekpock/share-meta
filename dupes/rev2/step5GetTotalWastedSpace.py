# Step 5
# Sum the size of all duplicate files.

import json
import os


def main():
    with open("hashSizes.txt", "r", encoding="utf-8") as file:
        hashSizes = json.load(file)

    with open("fileHashes.txt", "r", encoding="utf-8") as file:
        data = json.load(file)

    # adj = {}
    # for line in data:
    #     adj[line["hash"]] = line["files"]
    # with open("fileHashes.txt", "w", encoding="utf-8") as file:
    #     json.dump(adj, file)

    sizeSum = 0
    numFiles = 0
    for fileHash, size in sorted(hashSizes.items(), key=lambda x: x[1], reverse=True):
        files = data[fileHash]
        numLiveFiles = 0
        for fileInList in files:
            if os.path.exists(fileInList):
                numLiveFiles += 1
            # else:
            #     print(file)
        sizeSum += size * (numLiveFiles - 1)
        numFiles += numLiveFiles - 1

    print(
        f"Total of {sizeSum} wasted bytes ({int((sizeSum / 1024) / 1024)} mib, {int(((sizeSum / 1024) / 1024) / 1024)} gib) across {numFiles} files."
    )


if __name__ == "__main__":
    main()
