# <reward>
import sys
import time
from azure.cognitiveservices.personalizer import PersonalizerClient
from azure.cognitiveservices.personalizer.models import RankRequest
from msrest.authentication import CognitiveServicesCredentials
import pandas as pd
import numpy as np
import math
import time
from datetime import datetime, date, timedelta
import pytz
from collections import Counter
import string
import pickle
import json
import os
from datetime import date
import http.client, urllib.request, urllib.parse, urllib.error, base64

from exe_functions_nudge import search_directory, relative_date

def get_reward_updates(pcp_dict, run_time):
    week_list_current = [str(d.date()) for d in pd.date_range(relative_date(run_time-timedelta(7), 0, 0), periods=7).to_pydatetime().tolist()]
    past_rewards_fois_current = [s + "*reward_updates*.csv" for s in week_list_current]
    reward_outputs_list_current = []
    for ext in past_rewards_fois_current:
        reward_outputs_list_current.extend(search_directory(os.path.abspath(os.curdir), ext))

    week_list_prior = [str(d.date()) for d in pd.date_range(relative_date(run_time-timedelta(14), 0, 0), periods=7).to_pydatetime().tolist()]
    past_rewards_fois_prior = [s + "*reward_updates*.csv" for s in week_list_prior]
    reward_outputs_list_prior = []
    for ext in past_rewards_fois_prior:
        reward_outputs_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))
    if len(reward_outputs_list_prior) == 0 and len(reward_outputs_list_current) >= 1:
        print("\nOnly one set of prior events detected.\n" +
              "\nThis will be reflected in the `RankRequest` call.\n")
        pcp_dict['reward'] = pd.read_csv(reward_outputs_list_current[-1])
    elif (len(reward_outputs_list_prior) == 0 and len(reward_outputs_list_current) == 0):
        print("\nNo reward data present.\n" +
              "\nThis should have been prevented earlier in the workflow.\n"
              "\nTerminating......\n")
    else:
        past_factor_fois_prior = [s + "*factor_assignment*.csv" for s in week_list_prior]
        factor_outputs_list_prior = []
        for ext in past_factor_fois_prior:
            factor_outputs_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))

    # Subset updated_pt_dict to what we need for reward calls and put in dataframe
    # create an Empty DataFrame object
    column_values = ['reward', 'frame_id', 'history_id', 'social_id', 'content_id', 'reflective_id', 'record_id', 'trial_day_counter', 
                     'flag_send_reward_value_tX']
    reward_updates = pd.DataFrame(columns=column_values)

    for pt,data_row in pcp_dict.iterrows():
        # Reward value, Rank_Id's
        if(data_row["flag_send_reward_value_t0"] == True and data_row["censor_date"] >= today):
            reward_row_t0 = [data_row["reward_value_t0"], data_row["rank_id_framing_t0"], data_row["rank_id_history_t0"],
                       data_row["rank_id_social_t0"], data_row["rank_id_content_t0"], data_row["rank_id_reflective_t0"],
                       data_row["record_id"], data_row["trial_day_counter"], "flag_send_reward_value_t0"]
            reward_updates.loc[len(reward_updates)] = reward_row_t0
        if(data_row["flag_send_reward_value_t1"] == True and data_row["censor_date"] >= yesterday):
            reward_row_t1 = [data_row["reward_value_t1"], data_row["rank_id_framing_t1"], data_row["rank_id_history_t1"],
                       data_row["rank_id_social_t1"], data_row["rank_id_content_t1"], data_row["rank_id_reflective_t1"],
                       data_row["record_id"], data_row["trial_day_counter"], "flag_send_reward_value_t1"]
            reward_updates.loc[len(reward_updates)] = reward_row_t1
       
    # Write csv as a log for what we're sending to Personalizer
    reward_updates.to_csv(fp, index=False)
    reward_updates = reward_updates.to_numpy()
    return reward_updates


def send_rewards(reward_updates, client):
    # column_values = ['reward', '
    #   frame_id', 'history_id', 'social_id', 'content_id', 'reflective_id',
    #   'study_id', 'trial_day_counter']
    for i in range(0,reward_updates.shape[0]):
        row = reward_updates[i, :]
        reward_val = row[0] 
        for j in range(1,6):
            if isinstance(row[j],str):
                print("reward_val: ", reward_val)
                print("event_id: ", row[j])
                client.events.reward(event_id=row[j], value=reward_val)
            

            ##############---- If checking for connection with Personalizer ###############
            # headers = {
            #     # Request headers
            #     'Content-Type': 'application/json-patch+json',
            #     'Ocp-Apim-Subscription-Key': '{subscription key}',
            # }

            # params = urllib.parse.urlencode({
            # })

            # try:
            #     conn = http.client.HTTPSConnection('westus2.api.cognitive.microsoft.com')
            #     conn.request("POST", "/personalizer/v1.0/events/{eventId}/reward?%s" % params, "{body}", headers)
            #     response = conn.getresponse()
            #     data = response.read()
            #     print(data)
            #     conn.close()
            # except Exception as e:
            #     print("[Errno {0}] {1}".format(e.errno, e.strerror))

            ################################################################################
