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
import copy


from patient_data_nudge import import_pt_info, import_pt_outcomes
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

print("Checking log list for redundancy....")
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
    sys.exit()
else:
    fp = build_path(os.path.abspath(os.curdir) + ("\\_ProgramLog"), str(run_time.date()) + "_RL_Personalizer_log.txt")

## 3. Check for certain files and load patient data or terminate program accordingly
print(("IMPORT NUDGE PCP AND PARTICIPANT DATA").center(100,"-"))
# try:
pcp_dict = import_pt_info(run_time)
# except FileNotFoundError:
#     print("Participant import failed. Check filenames and re-run.")

#This is causing the hang
# 3. Start log for program

# old_stdout = sys.stdout        
# log_file = open(fp, "w")
# sys.stdout = log_file

## 3. Start main body of program

print(("BEGIN PROGRAM").center(100,"-"))

print(str(run_time))

## Set Up MS Azure Personalizer Client
print(("CREATE PERSONALIZER CLIENT").center(100,"-"))

with open(build_path(os.path.abspath(os.curdir) + ("\\.keys"), "azure-personalizer-key.txt"), 'r') as f:
     personalizer_key = f.read().rstrip()
client = PersonalizerClient(
    "https://bwh-pharmacoepi-roybal-dev-e2-ehr-cog.cognitiveservices.azure.com/", 
    CognitiveServicesCredentials(personalizer_key)
)


print(("CHECKING FOR AVAILABLE REWARD DATA").center(100,"-"))


if pcp_dict['reward'] == True:
    pcp_dict = import_pt_outcomes(pcp_dict,run_time)
    pcp_dict = get_reward_updates(pcp_dict, run_time)
    send_rewards(pcp_dict, client)
else:
    pcp_dict.pop('reward', None)

## Rank Step
# Call Personalizer to rank action features to find the correct EHR message to send today.

#ranked_pt_data = new_empty_pt_data()
#ranking_log = new_empty_rank_log(run_time)


print(("RANKING PCPS").center(100,"-"))


ranking_log = []
ehr_log = []
for pcp in pcp_dict['pcp']['study_id'].unique():
    pcp_unique = copy.deepcopy(pcp_dict)
    for key in pcp_unique.keys():
        #print(pcp)
        pcp_unique[key]=pcp_unique[key][pcp_unique[key].study_id.isin([pcp])]
        #print(pcp_unique)
    pcp_rank_log, pcp_ehr_log = run_ranking(pcp, pcp_unique, client)
    #pcp_rank_log, pcp_ehr_log = run_ranking(pcp, pcp_unique, client, run_time)
    ranking_log.append(pcp_rank_log)
    ehr_log.append(pcp_ehr_log)

# for index, patient in pt_data.iterrows():
#     if patient["censor"] != 1 and pd.Timestamp(patient["censor_date"], tz='US/Eastern') > run_time:
#         patient, pt_rank_log = run_ranking(patient, client, run_time)
#         ranked_pt_data = ranked_pt_data.append(patient)
#         ranking_log = ranking_log.append(pt_rank_log)

print(("EXPORT RANK LOG FILE").center(100,"-"))
ranking_log = generate_rank_log(ranking_log, run_time)
# ## Output SMS and Patient Data

print(("EXPORT EHR FILE").center(100,"-"))
ehr_log = write_ehr_history(ehr_log, run_time)
# ranked_pt_data.to_csv(
#     build_path(os.path.abspath(os.curdir) + ("\\000_PatientData"), str(run_time.date()) + "_pt_data.csv"), 
#     index=False
# )

print(("UPDATING WEEKLY METRICS").center(100,"-"))
update_weekly_vars(pcp_dict, ranking_log, run_time)

print(("-").center(100,"-"))
# log_file.close()
# sys.stdout = old_stdout

print(("PROGRAM SUCCESSFULLY RAN").center(100,"-"))

input("SUCCESSFULLY RAN TODAY: {} \n".format(run_time.strftime("%B %d, %Y"))
        + "Now, send EHR messages to providers from os.path.abspath " +
        (os.curdir) + ("\\000_Factor_Assignment\\") + str(run_time.date()) + "_factor_assignment.csv" +
        "\nPress Enter to exit the program and close this window.")
sys.exit()