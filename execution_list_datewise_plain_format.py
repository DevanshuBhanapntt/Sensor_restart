#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timedelta

def fetch_execution_job_ids(limit, start_time_gt, end_time_lt):
    #If below api key is not working create a new api key by using below command
    #st2 apikey create -k -m '{"test_key": "test api key"}'
    api_key = "API_KEY"
    stackstorm_ip_port = "127.0.0.1:9101"
    execution_url = "http://" + stackstorm_ip_port + "/v1/executions?st2-api-key=" + api_key + "&limit=" + limit + "&timestamp_gt=" + start_time_gt + "&timestamp_lt=" + end_time_lt + "&include_attributes=id,action.ref,context.user,status,start_timestamp,end_timestamp&sort_desc=True&parent=null"
    try:
        job_ids = requests.request('GET', execution_url)
    except Exception as e:
        print("Error while fetching execution details. Error is: {}".format(e))
        job_ids = ""
    dict_data = job_ids.json()
    if isinstance(dict_data, dict):
        print("Error is: {}".format(dict_data['faultstring']))
        exit(-1)
    print('[Latest job is first]')
    print("execution_id, workflow, status, elapsed_time, user, start_timestamp, end_timestamp")
    for item in dict_data:
        try:
            workflow = item['action']['ref']
        except Exception as e:
            workflow = "ACTION_ERROR"

        try:
            status = item['status']
        except Exception as e:
            status = "STATUS_ERROR"

        try:
            user = item['context']['user']
        except Exception as e:
            user= "USER_ERROR"

        try:
            start_timestamp = item['start_timestamp']
        except Exception as e:
            start_timestamp = "START_TIMESTAMP_ERROR"

        try:
            end_timestamp = item['end_timestamp']
        except Exception as e:
            end_timestamp = 'WORKFLOW_IS_IN_RUNNING_STATUS'

        try:
            id = item["id"]
        except Exception as e:
            id = "ID_ERROR"
        time_start = str(convert_date_time(start_timestamp)).split('.')[0] + " UTC"
        time_end = str(convert_date_time(end_timestamp)).split('.')[0] + " UTC"
        execution_time = str(elapsed_time(start_timestamp, end_timestamp)).split('.')[0] + "s"

        output = id + ", " + workflow + ", " + status + ", " + execution_time + ", " + user + ", " + time_start + ", " + time_end
        print(output)


def convert_date_time(date_value):
    try:
        convert_date = datetime.strptime(date_value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception as e:
        convert_date = date_value
    return convert_date

def elapsed_time(start_time, end_time):
    try:
        execution_start_time = convert_date_time(start_time)
        execution_end_time = convert_date_time(end_time)
        elapsed_timestamp = execution_end_time - execution_start_time
    except Exception as e:
        current_time = convert_date_time(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        utc_time = current_time + timedelta(hours=4, minutes=0) #Server time zone is EDT. Execution timestamps are in UTC. Convert current time to UTC format.
        elapsed_timestamp = (utc_time - execution_start_time)
        #elapsed_timestamp = "ERROR."
    return elapsed_timestamp


if __name__ == '__main__':
    if len(sys.argv) >= 4:
        limit = sys.argv[1]
        time_gt = sys.argv[2]
        time_lt = sys.argv[3]
        start_time_gt = time_gt.replace(' ', 'T') + ".000Z"
        end_time_lt = time_lt.replace(' ', 'T') + ".000Z"

        fetch_execution_job_ids(limit, start_time_gt, end_time_lt)
    else:
        print("Limit, start time and end time is required to fetch the execution list")
        print("Ex: python3 {} 10 '2022-12-17 00:00:00' '2022-12-17 23:59:59'".format(sys.argv[0]))
