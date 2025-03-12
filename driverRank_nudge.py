# <Dependencies>
from azure.cognitiveservices.personalizer import PersonalizerClient
from azure.cognitiveservices.personalizer.models import RankRequest
from msrest.authentication import CognitiveServicesCredentials
from Actions import get_framing_actions, get_history_actions, get_social_actions, get_content_actions, get_reflective_actions
from Actions_nudge import get_OpenEnc_actions, get_Simplification_actions, get_ColdState_actions, get_RiskFraming_actions
from datetime import datetime, date, timedelta
import sys
import os
import copy
import numpy as np
import pandas as pd

from itertools import groupby
from exe_functions import build_path

def update_weekly_vars(pcp_dict, ranking_log, run_time):
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_Past_Factor_Assignment"), str(run_time.date()) + "_past_factor_assignment.csv")
    if pcp_dict['pcp'][[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]].shape[1]==1:
        week_update = pcp_dict['pcp'][[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]].assign(nb_weeks_since_encounter=0, nb_weeks_since_coldstate=0, nb_weeks_since_simplification = 0, nb_weeks_since_riskframing = 0)
    else:
        week_update = pcp_dict['pcp'][[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]]
        week_update = pd.merge(week_update,ranking_log, on=["study_id"])
        week_update['nb_weeks_since_encounter'] = week_update.apply(lambda X: 0 if X.response_action_id_OpenEnc == 'yesOpenEnc' else X.nb_weeks_since_encounter + 1, axis=1)
        week_update['nb_weeks_since_coldstate'] = week_update.apply(lambda X: 0 if X.response_action_id_ColdState == 'yesColdState' else X.nb_weeks_since_coldstate + 1, axis=1)
        week_update['nb_weeks_since_simplification'] = week_update.apply(lambda X: 0 if X.response_action_id_Simplification == 'yesSimplification' else X.nb_weeks_since_simplification + 1, axis=1)
        week_update['nb_weeks_since_riskframing'] = week_update.apply(lambda X: 0 if X.response_action_id_RiskFrame == 'yesRiskFrame' else X.nb_weeks_since_riskframing + 1, axis=1)
        week_update = week_update[[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]]
        week_update.to_csv(fp, index=False)
    return None

def generate_rank_log(ranking_log, run_time):
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_RankData"), str(run_time.date()) + "_rank_log.csv")
    ranking_log = pd.DataFrame(ranking_log[0:],columns=['study_id','weekly_counter', 'response_action_id_OpenEnc', 'noOpenEnc', 'yesOpen', 'response_action_id_Simplification', 'noSimplification', 'yesSimplification', 'response_action_id_ColdState', 'noColdState', 'yesColdState', 'response_action_id_RiskFrame', 'noRiskFrame', 'yesRiskFrame'])
    ranking_log.to_csv(fp, index=False)
    return(ranking_log)

def write_ehr_history(ehr_log, run_time):
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_Factor_Assignment"), str(run_time.date()) + "_factor_assignment.csv")
    ehr_log = pd.DataFrame(ehr_log[0:],columns=['study_id', 'weekly_counter', 'openencounter_yn', 'simplification_yn', 'coldstate_yn', 'riskframing_yn'])
    conditions = [
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(1) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(1) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(1) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(0)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(1)),
        (ehr_log["openencounter_yn"].eq(0) & ehr_log["simplification_yn"].eq(0) & ehr_log["coldstate_yn"].eq(0) & ehr_log["riskframing_yn"].eq(0)),
        ]
    
    arm = list(range(1,17))
      
    ehr_log['arm_number'] = np.select(conditions, arm)
    
    ehr_log['arm_description'] = ehr_log["arm_number"].case_when([
        (ehr_log.eval("arm_number == 1"), "Open encounter alert, simplified language, message sent 2 days before visit, alternative risk framing language"),
        (ehr_log.eval("arm_number == 2"), "Open encounter alert, simplified language, message sent 2 days before visit"),
        (ehr_log.eval("arm_number == 3"), "Open encounter alert, message sent 2 days before visit, alternative risk framing language"),
        (ehr_log.eval("arm_number == 4"), "Open encounter alert, message sent 2 days before visit"),
        (ehr_log.eval("arm_number == 5"), "Open encounter alert, simplified language, alternative risk framing language"),
        (ehr_log.eval("arm_number == 6"), "Open encounter alert, simplified language"),
        (ehr_log.eval("arm_number == 7"), "Open encounter alter, alternative risk framing language"),
        (ehr_log.eval("arm_number == 8"), "Open encounter alert"),
        (ehr_log.eval("arm_number == 9"), "Order entry alert, simplified language, message sent 2 days before visit, alternative risk framing language"),
        (ehr_log.eval("arm_number == 10"), "Order entry alert, simplified language, message sent 2 days before visit"),
        (ehr_log.eval("arm_number == 11"), "Order entry alert, message sent 2 days before visit, alternative risk framing language"),
        (ehr_log.eval("arm_number == 12"), "Order entry alert, message sent 2 days before visit"),
        (ehr_log.eval("arm_number == 13"), "Order entry alert, simplified language, alternative risk framing language"),
        (ehr_log.eval("arm_number == 14"), "Order entry alert, simplified language"),
        (ehr_log.eval("arm_number == 15"), "Order entry alert, alternative risk framing language"),
        (ehr_log.eval("arm_number == 16"), "Control (no factor assignment")
        ])
    
    # Writes CSV for RA to send ehr messages.
    ehr_log.to_csv(fp, index=False)
    return(ehr_log)

def run_ranking(pcp, pcp_unique, client):
    """Send rank calls to Personalizer and update corresponding patient variables.

    1. Shift rank ids
    2. Make rank calls (framing, history, social, content, reflective)
        a. construct event_id
        b. get context features
        c. get actions
        d. call RankRequest
        e. get response, convert to int
        f. update patient var
    3. Update patient num days since rank calls
    4. Update appropriate sms vars in patient row
    """
    try:
        week_count = max(pcp_unique['reward']['weekly_counter'])+1
    except:
        week_count = 1
    
    # Creating and empty dataframe and filling it is memory inefficient
    # Creating a list, filling it, then converting to a dataframe is better:
    # https://stackoverflow.com/questions/13784192/creating-an-empty-pandas-dataframe-and-then-filling-it
    ranking_log = [pcp, (week_count)]
    ehr_log = [pcp, (week_count)]
    
    # Open Encounter
    rank_id_OpenEnc = pcp + "_" + str(week_count).rjust(2,"0") + "_OpenEnc"
    #patient["rank_id_OpenEnc_t0"] = rank_id_OpenEnc
    context = get_context(pcp, pcp_unique)
    actions = get_OpenEnc_actions()
    OpenEnc_rank_request = RankRequest(actions=actions, context_features=context, event_id=rank_id_OpenEnc)
    OpenEnc_response = client.rank(rank_request=OpenEnc_rank_request)
    OpenEnc_ranked = OpenEnc_response.reward_action_id
    
    ranking_log.append(OpenEnc_ranked)
    ranking_log.append(sorted(OpenEnc_response.as_dict()['ranking'], key=lambda i: i["id"])[0]['probability'])
    ranking_log.append(sorted(OpenEnc_response.as_dict()['ranking'], key=lambda i: i["id"])[1]['probability'])
    
    print(OpenEnc_response.as_dict())
    
    if OpenEnc_ranked == "yesOpenEnc":
        ehr_log.append(1)
    else:
        ehr_log.append(0)
    
    # Simplification
    rank_id_Simplification = pcp + "_" + str(week_count).rjust(2,"0") + "_Simplification"
    #patient["rank_id_Simplification_t0"] = rank_id_Simplification
    context = get_context(pcp, pcp_unique)
    actions = get_Simplification_actions()
    Simplification_rank_request = RankRequest(actions=actions, context_features=context, event_id=rank_id_Simplification)
    Simplification_response = client.rank(rank_request=Simplification_rank_request)
    Simplification_ranked = Simplification_response.reward_action_id
    
    ranking_log.append(Simplification_ranked)
    ranking_log.append(sorted(Simplification_response.as_dict()['ranking'], key=lambda i: i["id"])[0]['probability'])
    ranking_log.append(sorted(Simplification_response.as_dict()['ranking'], key=lambda i: i["id"])[1]['probability'])
    
    print(Simplification_response.as_dict())
    
    if Simplification_ranked == "yesSimplification":
        ehr_log.append(1)
    else:
        ehr_log.append(0)
    
    # Cold State
    rank_id_ColdState = pcp + "_" + str(week_count).rjust(2,"0") + "_ColdState"
    #patient["rank_id_ColdState_t0"] = rank_id_ColdState
    context = get_context(pcp, pcp_unique)
    actions = get_ColdState_actions()
    ColdState_rank_request = RankRequest(actions=actions, context_features=context, event_id=rank_id_ColdState)
    ColdState_response = client.rank(rank_request=ColdState_rank_request)
    ColdState_ranked = ColdState_response.reward_action_id
    
    ranking_log.append(ColdState_ranked)
    ranking_log.append(sorted(ColdState_response.as_dict()['ranking'], key=lambda i: i["id"])[0]['probability'])
    ranking_log.append(sorted(ColdState_response.as_dict()['ranking'], key=lambda i: i["id"])[1]['probability'])
    
    print(ColdState_response.as_dict())
    
    if ColdState_ranked == "yesColdState":
        ehr_log.append(1)
    else:
        ehr_log.append(0)
    
    # Risk Framing
    rank_id_RiskFraming = pcp + "_" + str(week_count).rjust(2,"0") + "_RiskFraming"
    #patient["rank_id_RiskFraming_t0"] = rank_id_RiskFraming
    context = get_context(pcp, pcp_unique)
    actions = get_RiskFraming_actions()
    RiskFraming_rank_request = RankRequest(actions=actions, context_features=context, event_id=rank_id_RiskFraming)
    RiskFraming_response = client.rank(rank_request=RiskFraming_rank_request)
    RiskFraming_ranked = RiskFraming_response.reward_action_id
    
    ranking_log.append(RiskFraming_ranked)
    ranking_log.append(sorted(RiskFraming_response.as_dict()['ranking'], key=lambda i: i["id"])[0]['probability'])
    ranking_log.append(sorted(RiskFraming_response.as_dict()['ranking'], key=lambda i: i["id"])[1]['probability'])
    
    print(RiskFraming_response.as_dict())
    
    if RiskFraming_ranked == "yesRiskFrame":
        ehr_log.append(1)
    else:
        ehr_log.append(0)
    return ranking_log, ehr_log



def shift_t0_t1_rank_ids(patient):
    # shift these values for the next rank to store t0 values  
    patient["reward_value_t1"] = patient["reward_value_t0"]
    patient["flag_send_reward_value_t1"] = patient["flag_send_reward_value_t0"]
    patient["rank_id_framing_t1"] = patient["rank_id_framing_t0"]
    patient["rank_id_history_t1"] = patient["rank_id_history_t0"]
    patient["rank_id_social_t1"] = patient["rank_id_social_t0"]
    patient["rank_id_content_t1"] = patient["rank_id_content_t0"]
    patient["rank_id_reflective_t1"] = patient["rank_id_reflective_t0"]
    patient["reward_value_t0"] = 0
    patient["flag_send_reward_value_t0"] = False
    patient["rank_id_framing_t0"] = None
    patient["rank_id_history_t0"] = None
    patient["rank_id_social_t0"] = None
    patient["rank_id_content_t0"] = None
    patient["rank_id_reflective_t0"] = None
    return patient

def get_context(pcp, pcp_unique):
    pcp_out = dict(enumerate(pcp_unique['pcp'][pcp_unique['pcp'].study_id.isin([pcp])].drop(columns='study_id').to_dict('records')))
    pcp_out['pcp'] = pcp_out.pop(0)
    pcp_out['patients'] = {}
    patframe = pcp_unique['patients'][pcp_unique['patients'].study_id.isin([pcp])].drop(columns='study_id')
    
    for index, pat_study_id in patframe.iterrows():
        patid = pat_study_id['pat_study_id']
        patout = dict(enumerate(patframe[patframe.pat_study_id.isin([patid])].drop(columns='pat_study_id').to_dict('records')))
        patout[patid] = patout.pop(0)
        pcp_out['patients'].update(patout)
    
    if 'reward' in pcp_unique:
        patout = dict(enumerate(pcp_unique['reward'][pcp_unique['reward'].study_id.isin([pcp])][[column for column in pcp_unique['reward'].columns if column.startswith('nb')]].to_dict('records')))
        patout['weekly_reward_info'] = patout.pop(0)
        pcp_out.update(patout)
        patout = pcp_unique['reward'][pcp_unique['reward'].study_id.isin([pcp])][[column for column in pcp_unique['reward'].columns if 'response_action_id' in column]].to_dict('records')
        patout = patout[0]
        keypat = list(patout.keys())
        keyval = list(patout.values())
        for keys in keypat:
            pcp_out[keys] = {}
            #pcp_out['past_rewards'] = {}
        for pairs in range(0,len(keypat)):
            #key, value = next((str(k), str(v)) for k, v in patout[0].items())
            #pout = {key: value}
            pcp_out[keypat[pairs]] = keyval[pairs]
            #pcp_out[key] = patout[0][key]
            #print(pcp_unique)
        
    context = [pcp_out]
    #Saving it as a dict instead of a list in order to call it for other information
    #Easily rectified but notable difference
    return(context)