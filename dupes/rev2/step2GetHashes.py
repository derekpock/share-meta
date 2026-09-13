# Step 2
# Read fileList.txt and output json in fileHashes.txt which dictionaries hashes to lists of files.
# Log of progress is stored in /tmp/dupeCheck.log.

import hashlib
import json

# from tqdm import tqdm


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


def main():
    with open("fileList.txt", "r", encoding="utf-8") as file:
        paths = file.readlines()

    fileHashes = {}
    with open("/tmp/getHashes.log", "w", encoding="utf-8") as log:
        i = 0
        total = len(paths)
        for path in paths:
            i += 1
            log.seek(0)
            log.write(f"{i} of {total}")
            log.flush()

            absPath = f"/share/{path[2:]}".strip()
            fileHash = hashFile(absPath)
            if fileHash in fileHashes:
                fileHashes[fileHash].append(absPath)
            else:
                fileHashes[fileHash] = [absPath]

    with open("fileHashes.txt", "w", encoding="utf-8") as file:
        json.dump(fileHashes, file)


if __name__ == "__main__":
    main()
