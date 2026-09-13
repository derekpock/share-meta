# Step 3
# For every hash in fileHashes.txt, save the size of the hash to a hashSizes.txt.

import json
import os


def main():
    with open("fileHashes.txt", "r", encoding="utf-8") as file:
        data = json.load(file)

    hashSizes = {}
    with open("/tmp/getSizes.log", "w", encoding="utf-8") as log:
        total = len(data.keys())
        step = 100
        for i, (key, value) in enumerate(data.items()):
            if i % step == 0:
                log.seek(0)
                log.write(f"{i} of {total} step {step}")
                log.flush()

            # print(f"{key} and {value[0]}")
            try:
                fileSize = os.path.getsize(value[0])
            except FileNotFoundError as e:
                print(e)
                fileSize = 0

            hashSizes[key] = fileSize

    with open("hashSizes.txt", "w", encoding="utf-8") as file:
        json.dump(hashSizes, file)


if __name__ == "__main__":
    main()
