#!/usr/bin/env python
# coding: utf-8

# imports individual libraries and tools installed in the virtual environment
import sys
import time
import dateutil
import dateutil.parser
from azure.cognitiveservices.personalizer import PersonalizerClient
from azure.cognitiveservices.personalizer.models import RankRequest
from msrest.authentication import CognitiveServicesCredentials
import pandas as pd
import numpy as np
import math
import time
from datetime import datetime, timedelta
from collections import Counter
import string
import pickle
import json
import pytz
import os
import re
import glob
import copy

# Imports the individual functions from `.py` files
from patient_data_nudge import import_pt_info
from driverReward_nudge import get_reward_updates, send_rewards
from driverRank_nudge import run_ranking, generate_rank_log, write_ehr_history, update_weekly_vars
from exe_functions_nudge import build_path, relative_date, remove_common, search_directory


## 1. Get date

print("getting runtime")
############# For real deal #############
run_time = datetime.now()
## standard python date libraries do not work on Windows machines
## so the pytz library is REQUIRED
run_time = pytz.timezone("America/New_York").localize(run_time)
#########################################

## 2. Check if program has been run this week

# The weekday() function indexes from 0-6, with the following corresponding to each day:
# 0 - Monday
# 1 - Tuesday
# 2 - Wednesday
# 3 - Thursday
# 4 - Friday
# 5 - Saturday
# 6 - Sunday

print("Checking log list for redundancy....\n")
# Generates a list of *.txt files in the \\_ProgramLog folder
loglist = glob.glob(os.path.abspath(os.curdir) + ("\\_ProgramLog\\*")+".txt")

# range is not an inclusive function so it has to be up to day 7 to include 0-6
#week_window = [build_path(os.path.abspath(os.curdir) + ("\\_ProgramLog"), str(d.date()) + "_RL_Personalizer_log.txt") for d in pd.date_range(relative_date(run_time, 0, 0), periods=7).to_pydatetime().tolist()]
week_window = [build_path(os.path.abspath(os.curdir) + ("\\_ProgramLog"), str(d.date()) + "_RL_Personalizer_log.txt") for d in pd.date_range(relative_date(run_time-timedelta(4), 4, 0), periods=10).to_pydatetime().tolist()]

# checks to see if any of the logs in the _ProgramLog directory come from the dates in "week_window"
if any(logfile in loglist for logfile in week_window):
    input("\nThe workflow seems to have been run already sometime between:\n" + [str(d.date()) for d in pd.date_range(relative_date(run_time-timedelta(4), 4, 0), periods=10).to_pydatetime().tolist()][0]
    + "\nto:\n"+ [str(d.date()) for d in pd.date_range(relative_date(run_time, 0, 0), periods=7).to_pydatetime().tolist()][6]
    + "\nIt will now automatically stop to avoid sending redundant information to Personalizer"
    + "\nPlease contact those involved to confirm if you are seeing this message in error.\n"
    + "Press Enter to exit the program and close this window.")
    sys.exit()
else:
    fp = build_path(os.path.abspath(os.curdir) + ("\\_ProgramLog"), str(run_time.date()) + "_RL_Personalizer_log.txt")

## 3. Check for certain files and load patient data or terminate program accordingly
print(("IMPORT NUDGE PCP AND PARTICIPANT DATA").center(100,"-") + "\n")

# This loads all the pcp and patient data as a dictionary full of dataframes
pcp_dict = import_pt_info(run_time)

if pcp_dict['pcp'].empty == True:
    print(("AGGREGATED PCP DATA PRODUCES EMPTY DATAFRAME").center(100,"-") + "\n")
    print(("Check the data and dates of files and re-run").center(100,"-") + "\n")
    sys.exit()

# 4. Start log for program
# Comment out the next 3 lines if you want to print to the terminal
# Otherwise all output will go to the log file
old_stdout = sys.stdout        
log_file = open(fp, "w")
sys.stdout = log_file

# 5. Start main body of program
# This is where the log output starts
print(("BEGIN PROGRAM").center(100,"-") + "\n")

print(str(run_time))

# 6. Set Up MS Azure Personalizer Client
print(("CREATE PERSONALIZER CLIENT").center(100,"-") + "\n")

with open(build_path(os.path.abspath(os.curdir) + ("\\.keys"), "azure-personalizer-key.txt"), 'r') as f:
     personalizer_key = f.read().rstrip()
client = PersonalizerClient(
    "https://bwh-pharmacoepi-roybal-dev-e2-ehr-cog.cognitiveservices.azure.com/", 
    CognitiveServicesCredentials(personalizer_key)
)

# 7. We checked for the reward data in step 3, this is just loading it
print(("CHECKING FOR AVAILABLE REWARD DATA").center(100,"-") + "\n")


if pcp_dict['reward'] == True:
    print(("PREVIOUS DATA FOUND, UPDATING").center(100,"-") + "\n")
    reward_bool = True
    pcp_dict = get_reward_updates(pcp_dict, run_time)
    if pcp_dict['reward'].empty == True:
        print(("AGGREGATED REWARD DATA PRODUCES EMPTY DATAFRAME").center(100,"-") + "\n")
        print(("Check the data and dates of files and re-run").center(100,"-") + "\n")
        print(("Mismatch between the weekly counter for rank_id and past factors are likely").center(100,"-") + "\n")
        # print(("-").center(100,"-") + "\n")
        # log_file.close()
        # sys.stdout = old_stdout
        sys.exit()
    print(pcp_dict['reward'])
    print("\n")
    send_rewards(pcp_dict, client)
else:
    print(("NO PREVIOUS DATA FOUND").center(100,"-") + "\n")
    pcp_dict.pop('reward', None)
    print("\n")
    reward_bool = False

# 8. Rank Step
# Call Personalizer to rank action features to find the correct EHR message to send today.

print(("Data to be sent to personalizer:").center(100,"-") + ":")

print(pcp_dict)

print("\n")

print(("RANKING PCPS").center(100,"-") + "\n")


ranking_log = []
ehr_log = []
for pcp in pcp_dict['pcp']['study_id'].unique():
    pcp_unique = copy.deepcopy(pcp_dict)
    for key in pcp_unique.keys():
        print(pcp)
        pcp_unique[key]=pcp_unique[key][pcp_unique[key].study_id.isin([pcp])]
        print(pcp_unique)
    pcp_rank_log, pcp_ehr_log = run_ranking(pcp, pcp_unique, client)
    ranking_log.append(pcp_rank_log)
    ehr_log.append(pcp_ehr_log)

print("\n")
print(("EXPORT RANK LOG FILE").center(100,"-") + "\n")
ranking_log = generate_rank_log(ranking_log, run_time)

# 9. Output EHR and Patient Data
print(ranking_log)
print("\n")

print(("EXPORT EHR FILE").center(100,"-") + "\n")
ehr_log = write_ehr_history(ehr_log, run_time)
print(ehr_log)
print("\n")

print(("UPDATING WEEKLY METRICS").center(100,"-") + "\n")
update_weekly_vars(pcp_dict, ranking_log, run_time)

print(("-").center(100,"-") + "\n")
log_file.close()
sys.stdout = old_stdout

print(("PROGRAM SUCCESSFULLY RAN").center(100,"-") + "\n")

input("SUCCESSFULLY RAN TODAY: {} \n".format(run_time.strftime("%B %d, %Y"))
        + "Now, send EHR messages to providers from os.path.abspath " +
        (os.curdir) + ("\\000_Factor_Assignment\\") + str(run_time.date()) + "_factor_assignment.csv" +
        "\nPress Enter to exit the program and close this window.")
sys.exit()