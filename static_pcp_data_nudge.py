import os
import pandas as pd
from exe_functions import build_path
import sys

from patient_data_nudge import get_pcp_study_ids, new_empty_pt_data
from exe_functions import build_path

def import_pcp_static_info(run_time):
    import_date = (run_time - pd.Timedelta("1 day")).date()
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_Static_PCP_Info"), str(import_date) + "_pcp_info.csv")
    #date_cols = ["start_date", "censor_date"]
    try:
        #pt_data = pd.read_csv(fp, sep=',', parse_dates=date_cols)
        pt_data = pd.read_csv(fp, sep=',')
    except FileNotFoundError:
        while True:
            first_day = input("\nIs today the trial initiation?\n" 
                      + "If today is the first day, type 'yes' then hit Enter.\n"
                      + "Otherwise type 'no' then hit Enter.\n"
                      + "Answer here: ").lower()
            if first_day in ["yes", "no"]:
                first_day = first_day == "yes"
                break
            else:
                print("Input was not 'yes' or 'no'. Please try again.")
        if not first_day:
            input("\n" + str(import_date) + "_pcp_info.csv in the 000_Static_PCP_Info folder not found.\n"
                  + "This file should always exist with yesterday's date in the name. Please contact Lily.\n"
                  + "Press Enter to exit the program and close this window.")
            sys.exit()
        pt_data = new_empty_provider_data()
        return pt_data
    return pt_data

def new_empty_provider_data():
    fp = build_path(os.path.abspath(os.curdir) + ("\\000_Static_PCP_Info"), "empty_start.csv")
    #date_cols = ["start_date", "censor_date"]
    #pt_data = pd.read_csv(fp, sep=',', header=0, parse_dates=date_cols)
    pt_data = pd.read_csv(fp, sep=',', header=0)
    return pt_data
