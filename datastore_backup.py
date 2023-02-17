#!/usr/bin/env python
import os
import subprocess
from datetime import datetime

backup_path = '/opt/scripts/logs/datastore_backup/'

def download_datastore_data():
   #backup_path = '/opt/scripts/logs/datastore_backup/'
    backup_name = datetime.now().strftime("%Y-%m-%d")
    backup_file = backup_path + "datastore_backup_" + str(backup_name) + ".json"
    print("File name is: {}".format(backup_file))
    try:
        datastore_backup = subprocess.Popen(["st2", "key", "list", "-d", "-n", "-1", "-j"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        output = datastore_backup.stdout.readlines()
    except Exception as e:
        output = []
    if output:
        with open(backup_file, "w") as backup_data:
            for item in output:
                backup_data.write(item.decode('utf-8'))
    else:
        print("Error while fetching datastore keys")

def remove_old_datastore_file():
    check_old_files = subprocess.Popen(['find', backup_path, '-type', 'f', '-name', 'datastore_backup_*.json', '-mtime', '+5'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    files_list = check_old_files.stdout.readlines()
    for item in files_list:
        file_name = item.decode('utf-8').strip()
        try:
            os.remove(file_name)
        except Exception as e:
            print("Unable to delete the file. Error is: {}".format(e))



if __name__ == "__main__":
    download_datastore_data()
    remove_old_datastore_file()

