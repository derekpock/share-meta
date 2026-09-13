# Step 4
# Filter fileHashes.txt into a list of duplicate files separated by empty lines in dupeHashes.txt.

import argparse
import json
import os


def main(focus: str, dropSolo: bool, nameRestriction: str):
    assert not (dropSolo and focus is None), "Cannot drop solo with no focus"

    with open("hashSizes.txt", "r", encoding="utf-8") as file:
        hashSizes = json.load(file)

    with open("fileHashes.txt", "r", encoding="utf-8") as file:
        data = json.load(file)

    # adj = {}
    # for line in data:
    #     adj[line["hash"]] = line["files"]
    # with open("fileHashes.txt", "w", encoding="utf-8") as file:
    #     json.dump(adj, file)

    with open("dupesFinal.txt", "w", encoding="utf-8") as file:
        for fileHash, size in sorted(
            hashSizes.items(), key=lambda x: x[1], reverse=True
        ):
            files = data[fileHash]
            fileCount = 0
            focusPresent = focus is None
            isSolo = True
            name = None
            nameRestrictionMet = nameRestriction != "different"
            for fileInList in files:
                if os.path.exists(fileInList):
                    fileCount += 1
                    if not focusPresent and focus in fileInList:
                        focusPresent = True
                    if dropSolo and focus not in fileInList:
                        isSolo = False
                    if nameRestriction is not None:
                        fileName = fileInList.split("/")[-1]
                        if name is None:
                            name = fileName
                        else:
                            if nameRestriction == "same" and name != fileName:
                                nameRestrictionMet = False
                            if nameRestriction == "different" and name != fileName:
                                nameRestrictionMet = True

            if (
                nameRestrictionMet
                and (not dropSolo or not isSolo)
                and focusPresent
                and fileCount > 1
            ):
                file.write(f"{size}\n")
                for dupe in files:
                    if os.path.exists(dupe):
                        file.write(f"{dupe}\n")
                file.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--focus")
    parser.add_argument("-d", "--drop-solo", action="store_true")
    parser.add_argument("-n", "--name", choices=["same", "different"])
    args = parser.parse_args()
    # print(args.name)
    main(args.focus, args.drop_solo, args.name)
