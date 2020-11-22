
import os
import datetime
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from data_classes.Patient import Patient
import pickle

def export_reward_data(reward_np_array):
    #WORK IN PROGRESS LOGGING FOR REWARD
    mac_path = "~/Dropbox (Partners HealthCare)/SHARED -- REINFORCEMENT LEARNING/Reward_Data/"
    pc_path = R"C:\Users\$USERNAME\Dropbox (Partners HealthCare)\SHARED -- REINFORCEMENT LEARNING\Reward_Data"

    pd.DataFrame(reward_np_array).to_csv("path/to/file.csv")


def export_pt_dict_pickle(pt_dict):
    filesave = str(date.today()) + "_patient_dict" + '.pickle'
    with open(filesave, 'wb') as fp:
        pickle.dump(pt_dict, fp)

def export_post_reward_pickle(pt_dict):
    filesave = str(date.today()) + "rewarded_patient_dict" + '.pickle'
    with open(filesave, 'wb') as fp:
        pickle.dump(pt_dict, fp)

def export_post_rank_pickle(pt_dict):
    filesave = str(date.today()) + "ranked_patient_dict" + '.pickle'
    with open(filesave, 'wb') as fp:
        pickle.dump(pt_dict, fp)

def write_data(pt_dict):
    #WORK IN PROGRESS FOR CONVERTING PICKLE TO CSV FILE FOR HUMAN READABILITY
    new_file = date.today().__str__()
    new_file = "PatientTrialData_" + new_file
    out_file = open(new_file, "w")
    out_file.write('variable headings')

    for patient in pt_dict:
        out_file.write(patient + '\n')

    out_file.close()