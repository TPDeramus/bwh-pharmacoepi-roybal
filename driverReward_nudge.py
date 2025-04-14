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
from janitor import clean_names, remove_empty
import string
import pickle
import json
import os
from datetime import date
import http.client, urllib.request, urllib.parse, urllib.error, base64

from functools import reduce
from exe_functions_nudge import search_directory, relative_date

def get_reward_updates(pcp_dict, run_time):
    week_list_current = [str(d.date()) for d in pd.date_range(relative_date(run_time-timedelta(14), 4, 0), periods=11).to_pydatetime().tolist()]
    past_rewards_fois_current = [s + "*patient_outcomes*.csv" for s in week_list_current]
    reward_outputs_list_current = []
    for ext in past_rewards_fois_current:
        reward_outputs_list_current.extend(search_directory(os.path.abspath(os.curdir), ext))

    past_factor_fois_prior = [s + "*factor_assignment*.csv" for s in week_list_current]
    factor_outputs_list_prior = []
    for ext in past_factor_fois_prior:
        factor_outputs_list_prior.extend(search_directory(os.path.abspath(os.curdir), ext))
        factor_outputs_list_prior = [entry for entry in factor_outputs_list_prior if "past" not in entry]
        
    rank_calls_fois_prior = [s + "*rank*log*.csv" for s in week_list_current]
    prior_rank_calls_outputs_list = []
    for ext in rank_calls_fois_prior:
        prior_rank_calls_outputs_list.extend(search_directory(os.path.abspath(os.curdir), ext))

    weekly_counter_fois = [s + "*past*factor_assignment*.csv" for s in week_list_current]
    weekly_counter_list = []
    for ext in weekly_counter_fois:
        weekly_counter_list.extend(search_directory(os.path.abspath(os.curdir), ext))
    
    if (len(reward_outputs_list_current) == 0 or len(factor_outputs_list_prior) == 0 or len(prior_rank_calls_outputs_list) == 0 or  len(weekly_counter_list) == 0):
        print("\nOne or more prior reward data is missing or absent.\n" +
               "\nThis should have been prevented earlier in the workflow.\n"
               "\nIf you are seeing this, check for missing files in these folders:\n")
        print("\nEHR_Patient_Outcomes:")
        print(reward_outputs_list_current)
        print("\nFactor_Assignment:")
        print(factor_outputs_list_prior)
        print("\nRank_Data:")
        print(prior_rank_calls_outputs_list)
        print("\nPast_Factor_Assignment:")
        print(weekly_counter_list)
        print("\nTerminating......\n")
        sys.exit()
    else:
        print("\nUpdated reward values for previous run to be calcualted from:")
        print(weekly_counter_list)
        
        #This loads the outcomes obtained for this week from last weeks model and scores them.
        patient_outcomes = pd.read_csv(reward_outputs_list_current[-1])
        
        patient_outcomes = patient_outcomes.clean_names(axis='columns')
        varlist = patient_outcomes.dtypes[patient_outcomes.dtypes != 'int64'][patient_outcomes.dtypes != 'float64'][patient_outcomes.dtypes !='datetime64[ns]'].index.tolist()
        if len(varlist) > 0:
            patient_outcomes = patient_outcomes.clean_names(axis=None, column_names=varlist, remove_special=False, strip_underscores = "both")
        
        # #Used from:
        # #https://stackoverflow.com/questions/54653356/case-when-function-from-r-to-python
        # conditions = [
        # (patient_outcomes["out_discontinuation_yn"].eq(1) & patient_outcomes["out_taper_yn"].eq(1)),
        # (patient_outcomes["out_open_smartset_yn"].eq(1) & patient_outcomes["out_no_order_yn"].eq(1)),
        # (patient_outcomes["out_override_reason_yn"].eq(1)),
        # ]
        
        # pt_reward_vals = [1,0.2,0.1]
        
        # patient_outcomes["reward_to_send"] = np.select(conditions, pt_reward_vals, default=0)
        
        # print("\nWeekly patient reward values are pulled from:")
        # print(reward_outputs_list_current)
        # print(patient_outcomes)
        
        # pcp_aggregates = patient_outcomes.groupby("study_id")[['reward_to_send']].mean().reset_index()
        # pcp_aggregates[pcp_aggregates['reward_to_send'] > 1] = 1
        # pcp_aggregates['reward_to_send'] = pcp_aggregates['reward_to_send'].round(2)
        
        # print("\nWeekly pcp aggregate rewards are:")
        # print(pcp_aggregates)
        
        
        #This loads the fator outcomes assigned from last week
        print("\nFactors from last week loaded into the context for personalizer are:")
        print(factor_outputs_list_prior)
        past_factors_data = pd.read_csv(factor_outputs_list_prior[-1])
        past_factors_data = past_factors_data.clean_names(axis='columns')
        varlist = past_factors_data.dtypes[past_factors_data.dtypes != 'int64'][past_factors_data.dtypes != 'float64'][past_factors_data.dtypes !='datetime64[ns]'].index.tolist()
        if len(varlist) > 0:
            past_factors_data = past_factors_data.clean_names(axis=None, column_names=varlist, remove_special=False, strip_underscores = "both")
        past_factors_data = past_factors_data.drop(columns=['arm_number', 'arm_description'])
        print(past_factors_data)
        
        #This loads the prior ranking information
        #ONLY study_id is cleaned by Janitor to prevent compatibility issues
        print("\nThe rank_ids and predicted results from last week's run are:")
        print(prior_rank_calls_outputs_list)
        prior_rank_data = pd.read_csv(prior_rank_calls_outputs_list[-1])
        #prior_rank_data = prior_rank_data.clean_names(axis='columns')
        #varlist = prior_rank_data.dtypes[prior_rank_data.dtypes != 'int64'][prior_rank_data.dtypes != 'float64'][prior_rank_data.dtypes !='datetime64[ns]'].index.tolist()
        if len(varlist) > 0:
            prior_rank_data = prior_rank_data.clean_names(axis=None, column_names=['study_id'], remove_special=False, strip_underscores = "both")
        prior_rank_data = prior_rank_data.loc[:,~prior_rank_data.columns.str.contains('yes|no', case=False)]
        print(prior_rank_data)
        
        #This loads the weekly assignment counts based on the rank data from last week
        print("\nThe rank_ids and predicted results from last week's run are:")
        print(weekly_counter_list)
        weekly_counter_data = pd.read_csv(weekly_counter_list[-1])
        weekly_counter_data = weekly_counter_data.clean_names(axis='columns')
        varlist = weekly_counter_data.dtypes[weekly_counter_data.dtypes != 'int64'][weekly_counter_data.dtypes != 'float64'][weekly_counter_data.dtypes !='datetime64[ns]'].index.tolist()
        if len(varlist) > 0:
            weekly_counter_data = weekly_counter_data.clean_names(axis=None, column_names=varlist, remove_special=False, strip_underscores = "both")
        print(weekly_counter_data)
        
        #Merges the data on the PCP level
        pcp_dict['reward'] = reduce(lambda  left,right: pd.merge(left,right, how='inner'), [pcp_dict['pcp'][['study_id']], patient_outcomes, prior_rank_data, past_factors_data, weekly_counter_data]).fillna('void')
        
    return pcp_dict


def send_rewards(pcp_dict, client):  
    for pt,data_row in pcp_dict['reward'].iterrows():
        if np.isnan(data_row['pt_reward_avg']) != True:
            #Added to account for the new format
            for column in data_row[['rank_id_OpenEnc', 'rank_id_Simplification', 'rank_id_ColdState', 'rank_id_RiskFraming']]:
                print("\nUpdating call " + column + "\n"
                  "\nwith reward value " + str(data_row['pt_reward_avg']) + "...\n")
                client.events.reward(event_id=column, value=data_row['pt_reward_avg'])
    pcp_dict['reward'] = pcp_dict['reward'].loc[:,~pcp_dict['reward'].columns.str.startswith('rank_id')]
    pcp_dict['reward'] = pcp_dict['reward'].drop(columns=['pt_reward_avg'])
    
    return pcp_dict