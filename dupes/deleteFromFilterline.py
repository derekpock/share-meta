# In VS Code, use the filter plugin within dupesFinal.txt to list certain files in dupesFinal.txt.filterline.txt
# Use this script if you want to delete all entries within the filtered output.

import os

with open("dupesFinal.txt.filterline.txt", "r", encoding="utf-8") as file:
    files = file.readlines()

for file in files:
    print(f"Would delete {file.strip()}")

response = input("Delete? y/N: ")
if not response.startswith("y"):
    print("Bailing")
    exit()

for file in files:
    try:
        os.remove(file.strip())
    except FileNotFoundError as e:
        print(e)
    except PermissionError as e:
        print(e)

print("Done")
