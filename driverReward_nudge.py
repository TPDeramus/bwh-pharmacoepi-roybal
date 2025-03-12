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

from functools import reduce
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

    if len(reward_outputs_list_prior) == 0 and len(reward_outputs_list_current) == 1:
        print("\nOnly one set of prior events detected.\n" +
              "\nThis will be reflected in the `RankRequest` call.\n")
        pcp_dict['reward'] = pd.read_csv(reward_outputs_list_current[-1])
    elif (len(reward_outputs_list_prior) == 0 and len(reward_outputs_list_current) == 0):
        print("\nNo reward data present.\n" +
              "\nThis should have been prevented earlier in the workflow.\n"
              "\nTerminating......\n")
    else:
        past_factor_fois_prior = [s + "*past*factor_assignment*.csv" for s in week_list_current]
        factor_outputs_list_prior = []
        for ext in past_factor_fois_prior:
            factor_outputs_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))
        rank_calls_fois_prior = [s + "*rank*log*.csv" for s in week_list_current]
        prior_rank_calls_outputs_list = []
        for ext in rank_calls_fois_prior:
            prior_rank_calls_outputs_list.extend(search_directory(os.path.abspath(os.curdir), ext))
        if len(factor_outputs_list_prior) == 0 or len(prior_rank_calls_outputs_list) == 0:
            print("\nFactor assignments or log files from previous week missing\n" +
                  "\nTerminating......\n")
            sys.exit()
        else:
            # Can't do a lambda merge due to the column missmatch
            #reduce(lambda  left,right: pd.merge(left,right,on=['study_id',], how='outer'), [pd.read_csv(reward_outputs_list_current[-1]),pd.read_csv(factor_outputs_list_prior[-1]),pd.read_csv(prior_rank_calls_outputs_list[-1])]).fillna('void')
            pcp_dict['reward'] = pd.merge(pd.merge(pd.read_csv(reward_outputs_list_current[-1]),pd.read_csv(prior_rank_calls_outputs_list[-1]), how="left", on=["study_id","weekly_counter"]),pd.read_csv(factor_outputs_list_prior[-1]), how="left", on=["study_id"])
            #pd.merge(pcp_dict['reward'],pd.read_csv(factor_outputs_list_prior[-1]), how="left", on=["study_id"])
    
    # #Previous tested workflow
    #     reward_fois_prior = [s + "*reward*updates.csv" for s in week_list_current]
    #     reward_output_list_prior = []
    #     for ext in reward_fois_prior:
    #         reward_output_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))

    #     pcp_dict['reward'] = pd.read_csv(reward_output_list_prior[-1])
    #     pcp_dict['reward']['reward'] = np.where(pcp_dict['reward']['reward'] == False, np.nan, pcp_dict['reward']['reward'])
    
    ##Current Workflow
        #reward_fois_prior = [s + "*reward*updates.csv" for s in week_list_current]
        #reward_output_list_prior = []
        #for ext in reward_fois_prior:
        #    reward_output_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))

        #pcp_dict['reward'] = pd.read_csv(reward_output_list_prior[-1])
        
        
        #reward_fois_prior = [s + "*rank*log.csv" for s in week_list_current]
        #reward_output_list_prior = []
        #for ext in reward_fois_prior:
        #    reward_output_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))
    
        #pcp_dict['reward'] = pd.merge(pcp_dict['reward'], pd.read_csv(reward_output_list_prior[-1]), how="left", on=["study_id"])
        
            pcp_dict['reward']['reward'] = np.where(pcp_dict['reward']['flag_send_reward_value_tX'] == "flag_send_reward_value_t0", np.nan, pcp_dict['reward']['reward'])
    return pcp_dict


def send_rewards(pcp_dict, client):  
    for pt,data_row in pcp_dict['reward'].iterrows():
        if np.isnan(data_row['reward']) != True:
            #Added to account for the new format
            for column in data_row[['OpenEnc_id','Simplification_id','ColdState_id','RiskFraming_id']]:
                print("\nUpdating call " + column + "\n"
                  "\nwith reward value " + str(data_row['reward']) + "...\n")
                client.events.reward(event_id=column, value=data_row['reward'])
