General workflow of this goes kind of like this:
- Make sure the hashes are updated with `python dupes.py hash`.
- Start with no filter and look at duplicates from `python dupes.py parse` and look over `dupesFinal.txt`.
- To narrow down a search query, use `python dupes.py parse -f "search"`, using `-r` for regex searches as needed.
- Depending on what's being searched, you may want to exclude duplicates that *only* match your search term. Use the `-d` option to do this with `parse`.
- When you're ready to delete a group of items, using VS Code's `Filter Line` plugin by `everettfj`, call `Filter Line By Input String` and search for the item you want to delete. **If you used `-d` with the same search query you used with `Filter Line` it is always safe to delete all filtered lines!**
- Once `Filter Line` outputs the filtered file, delete these items using `python deleteFromFilterline.py`, verifying the deletions.
- Repeat at the first step, regenerating the hash list, as updating the hashes is necessary to remove the now resolved duplicates.
- Also use `python dupes.py stat` for info on current hashes and duplicated space.

Example:
- Search focus "SAM" for duplicates of image files.
- If you want to delete the raw image and keep the duplicates found elsewhere, search focus "SAM" with -d so that only groups that have at least one non "SAM" entry exist.
- Filter Line by "SAM".
- Delete the listed files to clear up all "SAM" duplicates that have a presence elsewhere.