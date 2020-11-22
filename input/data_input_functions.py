import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from data_classes.Patient import Patient
import pickle
from output.data_output_functions import export_pt_dict_pickle
import os.path



# Imports Pillsy File and Convert to Numpy array
def import_Pillsy():
    pillsy_filename = str(date.today()-pd.Timedelta("1 day")) + "_pillsy" + '.csv'
    fp = os.path.join("..", "..", "..", "Pillsy", pillsy_filename)
    date_cols = ["eventTime"]
    pillsy = pd.read_csv(fp, sep=',', parse_dates=date_cols)
    pillsy.drop("patientId", axis=1, inplace=True)
    pillsy.drop("lastname", axis=1, inplace=True)
    pillsy.drop("method", axis=1, inplace=True)
    pillsy.drop("platform", axis=1, inplace=True)
    return pillsy

def import_redcap():
    redcap_filepath = str(date.today()) + "_redcap" + '.csv'
    date_cols = ["start_date"]
    redcap = pd.read_csv(redcap_filepath, sep=',', parse_dates=date_cols)
    return redcap

def load_dict_pickle():
    pickle_filename = str(date.today()-pd.Timedelta("1 day")) + "_patient_dict" + '.pickle'
    fp = os.path.join("..", "..", "PatientData", pickle_filename)
    # Used to represent the current patient data
    #   - i.e. before update with Pillsy from yesterday / what would be used for tomorrow's run
    with open(fp, 'rb') as pfile:
        pickle_dict = pickle.load(pfile)
    return pickle_dict

if __name__ == '__main__':
    load_dict_pickle()