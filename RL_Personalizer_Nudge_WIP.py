#!/usr/bin/env python
# coding: utf-8

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

from patient_data import import_pt_data, new_empty_pt_data
from patient_data_nudge import import_pt_info, import_pt_outcomes
from driverReward_nudge import get_reward_updates, send_rewards
from driverRank import run_ranking, write_sms_history, new_empty_rank_log, write_rank_log
from exe_functions_nudge import build_path, relative_date, remove_common, search_directory


## 1. Get date

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

# Generates a list of *.txt files in the \\_ProgramLog folder
loglist = glob.glob(os.path.abspath(os.curdir) + ("\\_ProgramLog\\*")+".txt")

# range is not an inclusive function so it has to be up to day 7 to include 0-6
week_window = [build_path(os.path.abspath(os.curdir) + ("\\_ProgramLog"), str(d.date()) + "_RL_Personalizer_log.txt") for d in pd.date_range(relative_date(run_time, 0, 0), periods=7).to_pydatetime().tolist()]

if any(logfile in loglist for logfile in week_window):
    input("\nThe workflow seems to have been run already sometime between:\n" + [str(d.date()) for d in pd.date_range(relative_date(run_time, 0, 0), periods=7).to_pydatetime().tolist()][0]
    + "\nto:\n"+ [str(d.date()) for d in pd.date_range(relative_date(run_time, 0, 0), periods=7).to_pydatetime().tolist()][6]
    + "\nIt will now automatically stop to avoid sending redundant information to Personalizer"
    + "\nPlease contact those involved to confirm if you are seeing this message in error.\n"
    + "Press Enter to exit the program and close this window.")
else:
    fp = build_path(os.path.abspath(os.curdir) + ("\\_ProgramLog"), str(run_time.date()) + "_RL_Personalizer_log.txt")


##This is causing the hang
## 3. Start log for program

# old_stdout = sys.stdout        
# log_file = open(fp, "w")
# sys.stdout = log_file

## 3. Start main body of program

print("-----------------------------BEGIN PROGRAM----------------------------")
print(str(run_time))

## 3. Check for certain files and load patient data or terminate program accordingly
print("--------------------IMPORT NUDGE PCP AND PARTICIPANT DATA-------------")
# try:
pcp_dict = import_pt_info(run_time)
# except FileNotFoundError:
#     print("Participant import failed. Check filenames and re-run.")

## Set Up MS Azure Personalizer Client
print("------------------------CREATE PERSONALIZER CLIENT--------------------")
with open(build_path(os.path.abspath(os.curdir) + ("\\.keys"), "azure-personalizer-key.txt"), 'r') as f:
     personalizer_key = f.read().rstrip()
client = PersonalizerClient(
    "https://bwh-pharmacoepi-roybal-dev-e2-ehr-cog.cognitiveservices.azure.com/", 
    CognitiveServicesCredentials(personalizer_key)
)

print("--------------------CHECKING FOR AVAILABLE REWARD DATA----------------")
if pcp_dict['reward'] == True:
    pcp_dict = import_pt_outcomes(pcp_dict,run_time)
    pcp_dict = get_reward_updates(pcp_dict, run_time)
    send_rewards(pcp_dict, client)

## Rank Step
# Call Personalizer to rank action features to find the correct EHR message to send today.

ranked_pt_data = new_empty_pt_data()
ranking_log = new_empty_rank_log(run_time)


print("---------------------------RANKING PCPS-------------------------------")
for pcps in pcp_dict['pcp']['study_id'].unique():


for index, patient in pt_data.iterrows():
    if patient["censor"] != 1 and pd.Timestamp(patient["censor_date"], tz='US/Eastern') > run_time:
        patient, pt_rank_log = run_ranking(patient, client, run_time)
        ranked_pt_data = ranked_pt_data.append(patient)
        ranking_log = ranking_log.append(pt_rank_log)

print("---------------------------------EXPORT RANK LOG FILE-----------------------------")
write_rank_log(ranking_log, run_time)
# ## Output SMS and Patient Data

print("---------------------------------EXPORT SMS FILE----------------------------------")
write_sms_history(ranked_pt_data, run_time)
ranked_pt_data.to_csv(
    build_path(os.path.abspath(os.curdir) + ("\\000_PatientData"), str(run_time.date()) + "_pt_data.csv"), 
    index=False
)

print("-----------------------------------------------------------------------------------")
#log_file.close()
#sys.stdout = old_stdout

print("---------------------------------PROGRAM SUCCESSFULLY RAN--------------------------")
input("SUCCESSFULLY RAN TODAY: {} \n".format(run_time.strftime("%B %d, %Y"))
        + "Now, send messages to patients from /000_SMS_TO_SEND/" + str(run_time.date()) + "_sms_history.csv"
        + "\nPress Enter to exit the program and close this window.")
sys.exit()