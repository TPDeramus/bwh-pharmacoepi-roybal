import os
import pandas as pd
from functools import reduce
from janitor import clean_names, remove_empty
from exe_functions import build_path
from datetime import datetime, timedelta
import sys
import glob
import re

from exe_functions_nudge import search_directory, relative_date

def import_pt_info(run_time):
    pcp_static_files = glob.glob(os.path.abspath(os.curdir) + ("\\000_Static_PCP_Info\\*.csv"))
    if(len(pcp_static_files) < 1):
        print("\nNo static PCP information found!\n"+
              "\nThis information is \033[1mREQUIRED\033[0m to launch the program.\n"+
              "\nTerminating......\n")
        sys.exit()
    else:
        li = []
        for filename in pcp_static_files:
            df = pd.read_csv(filename, index_col=None, header=0)
            li.append(df)
        pcp_static_data = pd.concat(li, axis=0, ignore_index=True)
        pcp_static_data['study_id'] = pcp_static_data['study_id'].str.lower()
    if len(glob.glob(os.path.abspath(os.curdir) + ("\\000_Past_Factor_Assignment\\*.csv"))) == 0:
        first_day = input("\nNo previous reward data detected.\n"
                          + "Is today the trial initiation?\n" 
                          + "If today is the first day, type 'yes' then hit Enter.\n"
                          + "Otherwise type 'no' then hit Enter.\n"
                          + "Answer here: ").lower()
        if first_day in ["yes", "no"]:
            if first_day == "yes":
                print("\nWorkflow will be run without prior reward data.\n")
                fois = ["*patient_info*.csv", "*pcp_info*.csv"]
                files_list = []
                for ext in fois:
                    files_list.extend(search_directory(os.path.abspath(os.curdir), ext))
                #print(files_list)
            else:
                start_date = input("\nNo start date identified, please type one below in the format YYYY-MM-DD.\n")
                try:
                    start_date = str(datetime.strptime(start_date, "%Y-%m-%d").date())
                    fois = [start_date + "*patient_info*.csv", start_date + "*pcp_info_weekly*.csv"]
                    files_list = []
                    for ext in fois:
                        files_list.extend(search_directory(os.path.abspath(os.curdir), ext))
                except SyntaxError:
                    print("Date format failed to parse!")
        else:
            print("\nInput was not 'yes' or 'no'. Please try again.\n")
            sys.exit()
        #print(files_list)
        if len(files_list) < 2 or (not all(any(item in file for file in files_list) for item in ["000_Patient_Info","000_Static_PCP_Info"])):
            print("\nNo starting PCP or Patient needed for study initiation found!\n"+
                  "\nTerminating......\n")
            #print(files_list)
            sys.exit()
        elif len(files_list) > 2:
            print("\nMultiple PCP or Patient files for study initiation found!\n"+
                  "\nPlease check the data for continuity at beginning of study.\n"+
                  "\nTerminating......\n")
            #print(files_list)
            sys.exit()
        else:
            print("\nPopulating dict variable.....\n")
            pcp_dict = {}
            print("\nReading in weekly PCP data.....\n")
            pcp_dynamic_data = pd.read_csv([s for s in files_list if "PCP" in s][0])
            pcp_dynamic_data['study_id'] = pcp_dynamic_data['study_id'].str.lower()
            pcp_dict['pcp'] = pd.merge(pcp_static_data, pcp_dynamic_data, on=['study_id'], how='inner')
            print("\nReading in Patient data.....\n")
            pcp_dict['patients'] = pd.read_csv([s for s in files_list if "Patient" in s][0])
            print("\nCleaning variable names with `janitor`.....\n")
            
            for frames in list(pcp_dict.keys()):
                pcp_dict[frames] = pcp_dict[frames].clean_names(axis='columns')
                varlist = pcp_dict[frames].dtypes[pcp_dict[frames].dtypes != 'int64'][pcp_dict[frames].dtypes != 'float64'][pcp_dict[frames].dtypes !='datetime64[ns]'].index.tolist()
                if len(varlist) > 0:
                    pcp_dict[frames] = pcp_dict[frames].clean_names(axis=None, column_names=varlist, remove_special=False, strip_underscores = "both")
                else:
                    continue
            print("\nVariable cleaning complete.\n")
            pcp_dict['reward'] = False
    else:
        #week_list = [str(d.date()) for d in pd.date_range(relative_date(run_time-timedelta(7), 0, 0), periods=7).to_pydatetime().tolist()]
        week_list = [str(d.date()) for d in pd.date_range(relative_date(run_time-timedelta(7), 4, 0), periods=11).to_pydatetime().tolist()]
        fois = [s + "*patient_info*.csv" for s in week_list] + [s + "*pcp_info_weekly*.csv" for s in week_list]
        files_list = []
        for ext in fois:
            files_list.extend(search_directory(os.path.abspath(os.curdir), ext))
        if len(files_list) < 2 or not all(any(item in file for file in files_list) for item in ["000_Patient_Info","000_PCP_Info_Weekly"]):
            print("\nNo weekly PCP or Patient info needed for weekly run found!\n")
            print("Check 'Patient_Info' and 'PCP_Info_Weekly' directories for filenames with the following dates:")
            print(week_list)
            print("\nTerminating......")
            sys.exit()
        elif len(files_list) > 2:
            print("\nMultiple PCP or Patient files found for this week!\n")
            print(files_list)
            
            print("\nPlease check the data for workflow continuity.\n"+
                  "\nTerminating......\n")
            sys.exit()
        else:
            print("\nPopulating dict variable.....\n")
            pcp_dict = {}
            print("\nReading in weekly PCP data.....\n")
            #pcp_dict['pcp'] = pd.read_csv([s for s in files_list if "PCP" in s][0])
            pcp_dynamic_data = pd.read_csv([s for s in files_list if "PCP" in s][0])
            pcp_dynamic_data['study_id'] = pcp_dynamic_data['study_id'].str.lower()
            pcp_dict['pcp'] = pd.merge(pcp_static_data, pcp_dynamic_data, on=['study_id'], how='inner')
            print("\nReading in weekly Patient data.....\n")
            pcp_dict['patients'] = pd.read_csv([s for s in files_list if "Patient" in s][0])
            print("\nCleaning variable names with `janitor`.....\n")
            for frames in list(pcp_dict.keys()):
                pcp_dict[frames] = pcp_dict[frames].clean_names(axis='columns')
                varlist = pcp_dict[frames].dtypes[pcp_dict[frames].dtypes != 'int64'][pcp_dict[frames].dtypes != 'float64'][pcp_dict[frames].dtypes !='datetime64[ns]'].index.tolist()
                if len(varlist) > 0:
                    pcp_dict[frames] = pcp_dict[frames].clean_names(axis=None, column_names=varlist, remove_special=False, strip_underscores = "both")
                else:
                    continue
            print("\nVariable cleaning complete.\n")
            pcp_dict['reward'] = True
    return pcp_dict

def get_pat_study_ids(pcp_dict):
    try:
    # Subsets the pat_study_id column to find the unique pat_study_id's for each patient
        pat_study_ids_df = pcp_dict['patients']['pat_study_id'].copy()
        unique_pat_study_ids_df = pat_study_ids_df.drop_duplicates()
        unique_pat_study_ids_list = unique_pat_study_ids_df.values.tolist()
    except ValueError:
        unique_pat_study_ids_list = []
    except TypeError:
        unique_pat_study_ids_list = []
    return unique_pat_study_ids_list

def get_pcp_study_ids(pcp_dict):
    try:
    # Subsets the study_id column to find the unique study_id's for each pcp
        pcp_study_ids_df = pcp_dict['pcp']['study_id'].copy()
        unique_pcp_study_ids_df = pcp_study_ids_df.drop_duplicates()
        pcp_unique_study_ids_list = unique_pcp_study_ids_df.values.tolist()
    except ValueError:
        pcp_unique_study_ids_list = []
    except TypeError:
        pcp_unique_study_ids_list = []
    return pcp_unique_study_ids_list