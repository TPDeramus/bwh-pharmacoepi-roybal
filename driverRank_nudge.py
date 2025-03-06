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
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_Past_Factor_Assigment"), str(run_time.date()) + "_past_factor_assignment.csv")
    if pcp_dict['pcp'][[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]]==1:
        week_update = pcp_dict['pcp'][[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]].assign(nb_weeks_since_encounter=0, nb_weeks_since_coldstate=0, nb_weeks_since_simplification = 0, nb_weeks_since_riskframing = 0)
    else:
        week_update = pcp_dict['pcp'][[column for column in pcp_dict['pcp'].columns if column.startswith('nb') or column.endswith('id')]]
        week_update = pd.merge(week_update,ranking_log, on=["study_id"])
        #pd.merge(,, how="left", on=["study_id"])
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
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_Factor_Assignment"), str(run_time.date()) + "_ehr_message_log.csv")
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
    
    # Writes CSV for RA to send text messages.
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
        week_count = 0
    
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
    
    print(OpenEnc_ranked)
    print(sorted(OpenEnc_response.as_dict()['ranking'], key=lambda i: i["id"]))
    
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
    
    print(Simplification_ranked)
    print(sorted(Simplification_response.as_dict()['ranking'], key=lambda i: i["id"]))
    
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
    
    print(ColdState_ranked)
    print(sorted(ColdState_response.as_dict()['ranking'], key=lambda i: i["id"]))
    
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
    
    print(RiskFraming_ranked)
    print(sorted(RiskFraming_response.as_dict()['ranking'], key=lambda i: i["id"]))
    
    if RiskFraming_ranked == "yesRiskFrame":
        ehr_log.append(1)
    else:
        ehr_log.append(0)

    #print(pt_rank_log)

    #patient = update_num_day_sms(patient)
    #patient = updated_sms_today(patient)
    #patient["trial_day_counter"] += 1
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


def update_framing_ranking(patient, response_action_id_framing):
    patient["response_action_id_framing"] = response_action_id_framing
    if patient["response_action_id_framing"] == "posFrame":
        patient["framing_sms"] = 1
    elif patient["response_action_id_framing"] == "negFrame":
        patient["framing_sms"] = 2
    elif patient["response_action_id_framing"] == "neutFrame":
        patient["framing_sms"] = 0
    return patient

def update_history_ranking(patient, response_action_id_history):
    patient["response_action_id_history"] = response_action_id_history
    if patient["response_action_id_history"] == "yesHistory":
        patient["history_sms"] = 1
    elif patient["response_action_id_history"] == "noHistory":
        patient["history_sms"] = 0
    return patient

def update_social_ranking(patient, response_action_id_social):
    patient["response_action_id_social"] = response_action_id_social
    if patient["response_action_id_social"] == "yesSocial":
        patient["social_sms"] = 1
    elif patient["response_action_id_social"] == "noSocial":
        patient["social_sms"] = 0
    return patient

def update_content_ranking(patient, response_action_id_content):
    patient["response_action_id_content"] = response_action_id_content
    if patient["response_action_id_content"] == "yesContent":
        patient["content_sms"] = 1
    elif patient["response_action_id_content"] == "noContent":
        patient["content_sms"] = 0
    return patient

def update_reflective_ranking(patient, response_action_id_reflective):
    patient["response_action_id_reflective"] = response_action_id_reflective
    if patient["response_action_id_reflective"] == "yesReflective":
        patient["reflective_sms"] = 1
    elif patient["response_action_id_reflective"] == "noReflective":
        patient["reflective_sms"] = 0
    return patient

def update_num_day_sms(patient):
    if patient["response_action_id_framing"] == "posFrame":
        patient["num_day_since_pos_framing"] = 0
        patient["num_day_since_neg_framing"] += 1
        patient["num_day_since_no_sms"] = 0
    elif patient["response_action_id_framing"] == "negFrame":
        patient["num_day_since_neg_framing"] = 0
        patient["num_day_since_pos_framing"] += 1
        patient["num_day_since_no_sms"] = 0
    elif patient["response_action_id_framing"] == "neutFrame":
        patient["num_day_since_neg_framing"] += 1
        patient["num_day_since_pos_framing"] += 1

    if patient["response_action_id_history"] == "yesHistory":
        patient["num_day_since_history"] = 0
        patient["num_day_since_no_sms"] = 0
    elif patient["response_action_id_history"] == "noHistory":
        patient["num_day_since_history"] += 1

    if patient["response_action_id_social"] == "yesSocial":
        patient["num_day_since_social"] = 0
        patient["num_day_since_no_sms"] = 0
    elif patient["response_action_id_social"] == "noSocial":
        patient["num_day_since_social"] += 1

    if patient["response_action_id_content"] == "yesContent":
        patient["num_day_since_content"] = 0
        patient["num_day_since_no_sms"] = 0
    elif patient["response_action_id_content"] == "noContent":
        patient["num_day_since_content"] += 1

    if patient["response_action_id_reflective"] == "yesReflective":
        patient["num_day_since_reflective"] = 0
        patient["num_day_since_no_sms"] = 0
    elif patient["response_action_id_reflective"] == "noReflective":
        patient["num_day_since_reflective"] += 1

    if patient["response_action_id_framing"] == "neutFrame":
        if patient["response_action_id_history"] == "noHistory" and patient["response_action_id_social"] == "noSocial" and patient["response_action_id_content"] == "noContent" and patient["response_action_id_reflective"] == "noReflective":
            patient["num_day_since_no_sms"] += 1
    
    return patient

# Computes and updates the SMS text message to send to this patient today.
def updated_sms_today(patient):
    fp = build_path(os.path.abspath(os.curdir) + ("\\_SMSChoices"), "sms_choices.csv")
    sms_choices = pd.read_csv(fp)
    framing = patient["framing_sms"]
    history = patient["history_sms"]
    social = patient["social_sms"]
    content = patient["content_sms"]
    reflective = patient["reflective_sms"]
    print("records_id: ", patient["record_id"]," rankresult: ", framing, history, social, content, reflective)

    rows = sms_choices[sms_choices['framing_sms'] == framing]
    rows = rows[rows['history_sms'] == history]
    rows = rows[rows['social_sms'] == social]
    rows = rows[rows['content_sms'] == content]
    rows = rows[rows['reflective_sms'] == reflective]

  
    # If 0,0,0,0,0 is found, then the rows will be None, so our defaults are first, the empty text message
    text_number = 0
    factor_set = 0
    text = ""
    text_message = ""
    quantitative_sms = 0
    doctor_sms = 0
    lifestyle_sms = 0
    
    # If 0,0,0,0,0 is not found, then the rows will have some potential values,
    if not rows.empty:
        # Then we randomize what of the factor set text messages we will send
        row = rows.sample()
        # We record the factor_set and text_number as unique identifiers for this message
        factor_set = row['factor_set'].item()
        text_number = row['text_number'].item()
        quantitative_sms = row['quantitative_sms'].item()
        doctor_sms = row['doctor_sms'].item()
        lifestyle_sms = row['lifestyle_sms'].item()

        text_message = row['text_message'].item()
        # We store the text message that will be sent for this specific patient that takes into account the history of their adherence
        # This finds and replaces the "X" in the sms_choices text_message rows to customize to the patient.
        text = row['text_message'].item().replace("X", str(patient["total_dichot_adherence_past7"]))

    # We've updated the local variables and now store into the patient object as attributes to be exported in bulk by another function
    patient["text_number"] = text_number
    patient["factor_set"] = factor_set
    patient["text_message"] = text_message
    patient["quantitative_sms"] = quantitative_sms
    patient["doctor_sms"] = doctor_sms
    patient["lifestyle_sms"] = lifestyle_sms
    patient["sms_msg_today"] = text
    return patient

# def get_demographics_features(patient):
#     demographic_features = {"age": patient["age"],
#                             "sex": patient["sex"],
#                             "race_white": patient["race_white"],
#                             "race_black": patient["race_black"],
#                             "race_asian": patient["race_asian"],
#                             "race_hispanic": patient["race_hispanic"],
#                             "race_other": patient["race_other"],
#                             "education_level": patient["edu_level"],
#                             "employment_status": patient["employment_status"],
#                             "marital_status": patient["marital_status"]}
#     demographic_features_dict = {"demographic_features": demographic_features}
#     return demographic_features_dict


# def get_clinical_features(patient):
#     clinical_features = {"num_physicians": patient["num_physicians"],
#                          "num_years_dm_rx": patient["num_years_dm_rx"],
#                          "hba1c": patient["hba1c"]}
#     clinical_features_dict = {"clinical_features": clinical_features}
#     return clinical_features_dict


# def get_motivational_features(patient):
#     motivational_features = {"automaticity": patient["automaticity"],
#                              "pt_activation": patient["pt_activation"],
#                              "reason_dm_rx": patient["reason_dm_rx"]}
#     motivational_features_dict = {"motivational_features": motivational_features}
#     return motivational_features_dict


# def get_rx_use_features(patient):
#     rx_use = {"num_rx": patient["num_rx"],
#               "concomitant_insulin_use": patient["concomitant_insulin_use"],
#               "non_adherence": patient["non_adherence"]}
#     rx_use_dict = {"rx_use": rx_use}
#     return rx_use_dict


# def get_pillsy_med_features(patient):
#     pillsy_med_features = {"num_twice_daily_pillsy_meds": patient["num_twice_daily_pillsy_meds"],
#                            "pillsy_meds_agi": patient["pillsy_meds_agi"],
#                            "pillsy_meds_dpp4": patient["pillsy_meds_dpp4"],
#                            "pillsy_meds_glp1": patient["pillsy_meds_glp1"],
#                            "pillsy_meds_meglitinide": patient["pillsy_meds_meglitinide"],
#                            "pillsy_meds_metformin": patient["pillsy_meds_metformin"],
#                            "pillsy_meds_sglt2": patient["pillsy_meds_sglt2"],
#                            "pillsy_meds_sulfonylurea": patient["pillsy_meds_sulfonylurea"],
#                            "pillsy_meds_thiazolidinedione": patient["pillsy_meds_thiazolidinedione"],
#                            "num_pillsy_meds": patient["num_pillsy_meds_t0"]}
#     pillsy_med_features_dict = {"pillsy_med_features": pillsy_med_features}
#     return pillsy_med_features_dict


# def get_observed_feedback_features(patient):
#     observed_feedback_features = {}
#     if patient["disconnectedness"] != None and patient["trial_day_counter"] >= 1:
#         observed_feedback_features["disconnectedness"] = patient["disconnectedness"]
#     if patient["early_rx_use"] != None and patient["trial_day_counter"] >= 1:
#         observed_feedback_features["early_rx_use"] = patient["early_rx_use"]
#     if (patient["avg_adherence_1day"] != None) and patient["trial_day_counter"] >= 1:
#         observed_feedback_features["avg_adherence_1day"] = patient["avg_adherence_1day"]
#     if (patient["avg_adherence_3day"] != None) and patient["trial_day_counter"] >= 3:
#         observed_feedback_features["avg_adherence_3day"] = patient["avg_adherence_3day"]
#     if (patient["avg_adherence_7day"] != None) and patient["trial_day_counter"] >= 7:
#         observed_feedback_features["avg_adherence_7day"] = patient["avg_adherence_7day"]
#     observed_feedback_features_dict = {"observed_feedback_features": observed_feedback_features}
#     return observed_feedback_features_dict



def get_num_days_since_features(patient):
    num_days_since_features = {"num_day_since_no_sms": patient["num_day_since_no_sms"],
                               "num_day_since_pos_framing": patient["num_day_since_pos_framing"],
                               "num_day_since_neg_framing": patient["num_day_since_neg_framing"],
                               "num_day_since_history": patient["num_day_since_history"],
                               "num_day_since_social": patient["num_day_since_social"],
                               "num_day_since_content": patient["num_day_since_content"],
                               "num_day_since_reflective": patient["num_day_since_reflective"]}
    num_days_since_features_dict = {"num_days_since_features": num_days_since_features}
    return num_days_since_features_dict


# def get_context(pcp):
#     statics = dict_df['000_Static_PCP_Info'][dict_df['000_Static_PCP_Info'].study_id.isin([pcp])].drop(columns='study_id')
#     patients = dict_df['000_Patient_Info'][dict_df['000_Patient_Info'].study_id.isin([pcp])].drop(columns='study_id')
#     past_factors = dict_df['000_Past_Factor_Assigment'][dict_df['000_Past_Factor_Assigment'].study_id.isin([pcp])].drop(columns='study_id')
#     ehr_outcomes = dict_df['000_EHR_Patient_Outcomes'][dict_df['000_EHR_Patient_Outcomes'].study_id.isin([pcp])].drop(columns='study_id')
    
#     if any(len(x) > 1 for x in [statics, past_factors]):
#         input("Multiple entries for static or past factors PCP variables detected for " + 
#               pcp +
#               "! The session will now terminate.")
#         sys.exit()
    
#     statics = {'sex_pcp': statics['sex_pcp'],
#                'race_pcp_cat': statics['race_pcp_cat'],
#                'providertype_cat': statics['providertype_cat'],
#                'specialty_cat': statics['specialty_cat'],
#                'yearsatatrius_int': statics['yearsatatrius_int'],
#                'panelsize_int': statics['panelsize_int'],
#                'prop_patient65plus': statics['prop_patient65plus'],
#                'avg_patientage': statics['avg_patientage'],
#                'avg_nb_patient_problems': statics['avg_nb_patient_problems'],
#                'avg_nb_appointments': statics['avg_nb_appointments'],
#                'avg_pct_encounters_closed_same_day': statics['avg_pct_encounters_closed_same_day'],
#                'avg_pct_orders_contrib_other_providers': statics['avg_pct_orders_contrib_other_providers'],
#                'avg_doc_length_per_appt': statics['avg_doc_length_per_appt'],
#                'avg_meds_per_appt_signed': statics['avg_meds_per_appt_signed'],
#                'avg_min_in_ehr_workday': statics['avg_min_in_ehr_workday'],
#                'avg_min_in_ehr_outisde_7a7p': statics['avg_min_in_ehr_outisde_7a7p'],
#                'avg_min_notes_appt': statics['avg_min_notes_appt'],
#                'avg_min_inbasket_appt': statics['avg_min_inbasket_appt'],
#                'avg_min_order_appt': statics['avg_min_order_appt'],
#                'avg_min_clinreview_appt': statics['avg_min_clinreview_appt'],
#                'avg_min_unscheduled_days': statics['avg_min_unscheduled_days'],
#                'avg_pct_orders_smartset': statics['avg_pct_orders_smartset'],
#                'admin_fte': statics['admin_fte']
#                }
    
#     past_factors = {'nb_weeks_since_encounter': past_factors['nb_weeks_since_encounter'],
#                     'nb_weeks_since_coldstate': past_factors['nb_weeks_since_coldstate'],
#                     'nb_weeks_since_simplification': past_factors['nb_weeks_since_simplification'],
#                     'nb_weeks_since_riskframing': past_factors['nb_weeks_since_riskframing']
#                     }
    
#     pcpcontext = {'pcp_demo': statics, 'pcp_practices': past_factors, 'patients' :{}}
    
#     for index, pat_study_id in patients.iterrows():
#         patid = pat_study_id['pat_study_id']
#         patient_features = {'pat_age': patients[patients.pat_study_id.isin([patid])]['pat_age'],
#                             'pat_sex': patients[patients.pat_study_id.isin([patid])]['pat_sex'],
#                             'pat_race': patients[patients.pat_study_id.isin([patid])]['pat_race'],
#                             'pat_language': patients[patients.pat_study_id.isin([patid])]['pat_language'],
#                             'encounter_weekday': patients[patients.pat_study_id.isin([patid])]['encounter_weekday'],
#                             'encounter_time': patients[patients.pat_study_id.isin([patid])]['encounter_time'],
#                             'hosp_last90days_yn': patients[patients.pat_study_id.isin([patid])]['hosp_last90days_yn'],
#                             'er_visit_last90days_yn': patients[patients.pat_study_id.isin([patid])]['er_visit_last90days_yn'],
#                             'dementia_yn': patients[patients.pat_study_id.isin([patid])]['dementia_yn'],
#                             'depression_yn': patients[patients.pat_study_id.isin([patid])]['depression_yn'],
#                             'anxiety_yn': patients[patients.pat_study_id.isin([patid])]['anxiety_yn'],
#                             'chronicpain_yn': patients[patients.pat_study_id.isin([patid])]['chronicpain_yn'],
#                             'insomnia_yn': patients[patients.pat_study_id.isin([patid])]['insomnia_yn'],
#                             'samepcp_yn': patients[patients.pat_study_id.isin([patid])]['samepcp_yn'],
#                             'days_since_last_pcpvisit': patients[patients.pat_study_id.isin([patid])]['days_since_last_pcpvisit'],
#                             'nb_pcp_visits_365days': patients[patients.pat_study_id.isin([patid])]['nb_pcp_visits_365days'],
#                             'pcp_prescribed_highriskmed_yn': patients[patients.pat_study_id.isin([patid])]['pcp_prescribed_highriskmed_yn'],
#                             'nb_eligible_meds': patients[patients.pat_study_id.isin([patid])]['nb_eligible_meds'],
#                             'benzo_yn': patients[patients.pat_study_id.isin([patid])]['benzo_yn'],
#                             'sedativehypnotic_yn': patients[patients.pat_study_id.isin([patid])]['sedativehypnotic_yn'],
#                             'anticholinergic_yn': patients[patients.pat_study_id.isin([patid])]['anticholinergic_yn'],
#                             'nb_pills_last180days': patients[patients.pat_study_id.isin([patid])]['nb_pills_last180days']}
#         patient_outcomes = {'out_discontinuation_yn': ehr_outcomes[ehr_outcomes.pat_study_id.isin([patid])]['out_discontinuation_yn'],
#                             'out_taper_yn': ehr_outcomes[ehr_outcomes.pat_study_id.isin([patid])]['out_taper_yn'],
#                             'out_open_smartset_yn': ehr_outcomes[ehr_outcomes.pat_study_id.isin([patid])]['out_open_smartset_yn'],
#                             'out_no_order_yn': ehr_outcomes[ehr_outcomes.pat_study_id.isin([patid])]['out_no_order_yn'],
#                             'out_override_reason_yn': ehr_outcomes[ehr_outcomes.pat_study_id.isin([patid])]['out_override_reason_yn'],
#                             'telemedicine_visit_yn': ehr_outcomes[ehr_outcomes.pat_study_id.isin([patid])]['telemedicine_visit_yn']}
#         pcpcontext['patients'].update({patid: {"patient_demo": patient_features, "patient_outcomes": patient_outcomes}})
#     pcpcontext = [pcpcontext]
#     return pcpcontext

def get_context(pcp,pcp_unique):
    pcp_out = dict(enumerate(pcp_unique['pcp'][pcp_unique['pcp'].study_id.isin([pcp])].drop(columns='study_id').to_dict('records')))
    pcp_out['pcp'] = pcp_out.pop(0)
    pcp_out['patients'] = {}
    patframe = pcp_unique['patients'][pcp_unique['patients'].study_id.isin([pcp])].drop(columns='study_id')
    
    for index, pat_study_id in patframe.iterrows():
        patid = pat_study_id['pat_study_id']
        patout = dict(enumerate(patframe[patframe.pat_study_id.isin([patid])].drop(columns='pat_study_id').to_dict('records')))
        patout[patid] = patout.pop(0)
        pcp_out['patients'].update(patout)
    context = [pcp_out]
    #Saving it as a dict instead of a list in order to call it for other information
    #Easily rectified but notable difference
    return(context)