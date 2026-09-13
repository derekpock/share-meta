import pathlib

root = pathlib.Path("../..")
with open("fileList.txt", "w", encoding="utf-8") as file:
    for path in root.rglob("*"):
        if not path.is_dir():
            file.write(f"{str(path)[4:]}\n")
# print(list(str(x) for x in root.rglob("*")))
