#!/bin/bash
# Check if any permissions are not "drwx" or "-rw"

ls -la .. -R | grep -v "\./\|^total\|drwx\|-rw" | strings
