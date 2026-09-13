#!/bin/bash

rm -f DONE
touch RUNNING

bash step1GetFiles.sh
python3 step2GetHashes.py
python3 step3GetSizes.py
python3 step4ListDupes.py
python3 step5GetTotalWastedSpace.py

rm -f RUNNING
touch DONE