import os
import sys
import glob
from os import path
from datetime import datetime, timedelta

def build_path(folder, fname):
	basedir = sys.executable
	bundle_dir = path.dirname(basedir)
	return path.abspath(path.join(bundle_dir, folder, fname))

def relative_date(reference, weekday, timevalue):
    hour, minute = divmod(timevalue, 1)
    minute *= 60
    days = reference.weekday() - weekday
    return (reference - timedelta(days=days)).replace(
        hour=int(hour), minute=int(minute), second=0, microsecond=0)

def remove_common(a, b):
    common = set(a) & set(b)
    a = [i for i in a if i not in common]
    b = [i for i in b if i not in common]
    return(a)

def search_directory(directory, string):
    results = glob.glob(directory +("/**/*") + (string), recursive=True)
    return(results)