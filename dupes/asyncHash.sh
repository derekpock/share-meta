#!/bin/bash

nohup python dupes.py hash > hash.log &
ps aux | grep -v grep | grep dupes
