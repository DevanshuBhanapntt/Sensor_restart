#!/usr/bin/env python3

import requests
import sys
import json
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, date


company = "ACCOUNT NAME"
company_abbreviation = "ACCOUNT SHORT NAME"
server_ip = "10.96.70.225"
msg_to = "BAO_Offshore_team@nttdata.com"
#msg_to = 'venkatanagababu.battina@nttdata.com'

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
    hour_list = []
    workflow_list = []
    all_list = []
    workflow_incidents_data = []
    for item in dict_data:
        try:
            workflow = item['action']['ref']
        except Exception as e:
            workflow = "ACTION_ERROR"

        try:
            status = item['status']
        except Exception as e:
            status = "STATUS_ERROR"

        workflow_sts = workflow + "*" + status
        workflow_list.append(workflow_sts)

        try:
            user = item['context']['user']
        except Exception as e:
            user= "USER_ERROR"

        try:
            start_timestamp = item['start_timestamp']
            hour = start_timestamp.split('T')[1].split(':')[0]
            hour_list.append(int(hour))
        except Exception as e:
            start_timestamp = "START_TIMESTAMP_ERROR"

        try:
            end_timestamp = item['end_timestamp']
        except Exception as e:
            end_timestamp = 'WORKFLOW_IS_IN_RUNNING_STATUS'

        try:
            workflow_id = item["id"]
        except Exception as e:
            workflow_id = "ID_ERROR"
        if status.lower() == "failed":
            incident_id = workflow_incident_details(stackstorm_ip_port, api_key, workflow_id)
            incidents_data = workflow + "*" + workflow_id + "*" + incident_id + "*" + status
            workflow_incidents_data.append(incidents_data)

        if int(str(datetime.now().hour)) >= 20 and int(str(datetime.now().hour)) <= 21:
            incidents_details = workflow_incident_details(stackstorm_ip_port, api_key, workflow_id)
            all_workflow_data = start_timestamp.split('.')[0].replace('T', ' ') + "*" + workflow_id + "*" + workflow + "*" + incidents_details + "*" + status
            all_list.append(all_workflow_data)


        time_start = str(convert_date_time(start_timestamp)).split('.')[0] + " UTC"
        time_end = str(convert_date_time(end_timestamp)).split('.')[0] + " UTC"
        execution_time = str(elapsed_time(start_timestamp, end_timestamp)).split('.')[0] + "s"

        output = workflow_id + ", " + workflow + ", " + status + ", " + execution_time + ", " + user + ", " + time_start + ", " + time_end
        #print(output)

    hour_counts_data = ""
    total_cnt = 0
    for hr_cnt in range(0,24):
        cnt = hour_list.count(hr_cnt)
        total_cnt += cnt
        print("{} hour count is: {}".format(hr_cnt, cnt))
        if int(hr_cnt) == int(str(datetime.now().hour)) + 5:  #To convert system hour value to UTC timezone. UTC is 5 hours ahead of EST
            hour_counts_data += "<tr align='center' style='background-color:#FFFF33'><td width='50%'>" + str(date.today()) + "  " + str(hr_cnt) +  ":00:00 **</td><td width='50%'>" + str(cnt) + "</td></tr>"
        else:
            hour_counts_data += "<tr align='center'><td width='50%'>" + str(date.today()) + "  " + str(hr_cnt) +  ":00:00</td><td width='50%'>" + str(cnt) + "</td></tr>"
    print("Total execuction count is: {}".format(total_cnt))

    unique_list = [*set(workflow_list)]
    temp_data = []
    action_cnt = 0
    for action_name in unique_list:
        cnt = workflow_list.count(action_name)
        action_cnt += cnt
        temp_data.append(action_name + "*" + str(action_cnt))
        #print("{} Count is: {}".format(action_name, action_cnt))
        action_cnt = 0
    temp_data.sort(key = lambda x:x.split('.')[1].split('*')[0])
    #print("Temp list is: {}".format(temp_data))

    total_success_cnt = 0
    total_failed_cnt = 0
    total_running_cnt = 0
    total_other_cnt = 0
    workflow_details = ""
    for item in temp_data:
        tbl_data = item.split('*')
        if tbl_data[1] == 'succeeded':
            workflow_details += "<tr align='center'><td width='33%'>" + tbl_data[0] + "<td width='33%' style='background-color:#C3FDB8'>" + tbl_data[1] + "<td width='33%'>" + tbl_data[2] + "</td></tr>"
            total_success_cnt += int(tbl_data[2])
        elif tbl_data[1] == 'failed':
            workflow_details += "<tr align='center'><td width='33%'>" + tbl_data[0] + "<td width='33%' style='background-color:#F98B88'>" + tbl_data[1] + "<td width='33%'>" + tbl_data[2] + "</td></tr>"
            total_failed_cnt += int(tbl_data[2])
        elif  tbl_data[1] == 'running':
            workflow_details += "<tr align='center'><td width='33%'>" + tbl_data[0] + "<td width='33%' style='background-color:#FFCE44'>" + tbl_data[1] + "<td width='33%'>" + tbl_data[2] + "</td></tr>"
            total_running_cnt += int(tbl_data[2])
        else:
            workflow_details += "<tr align='center'><td width='33%'>" + tbl_data[0] + "<td width='33%' style='background-color:#9AFEFF'>" + tbl_data[1] + "<td width='33%'>" + tbl_data[2] + "</td></tr>"
            total_other_cnt += int(tbl_data[2])

    failed_incs_data = ""
    for item_data in workflow_incidents_data:
        incs = item_data.split('*')
        failed_incs_data += """<tr align='center'><td width='25%'>""" + incs[0] + """</td>
                               <td width='25%'>""" + incs[1] + """</td>
                               <td width='25%'>""" + incs[2] + """</td>
                               <td width='25%' style='background-color:#F67280'>""" + incs[3] + """</td></tr>"""

    today_all_data = ""
    for all_data in all_list[::-1]:
        all_workflows = all_data.split('*')
        today_all_data += """<tr align='center'><td width='25%'>""" + all_workflows[0] + """</td>
                               <td width='25%'>""" + all_workflows[1] + """</td>
                               <td width='25%'>""" + all_workflows[2] + """</td>
                               <td width='25%'>""" + all_workflows[3] + """</td> """
        if all_workflows[4] == 'succeeded':
            today_all_data += """<td width='25%' style='background-color:#C3FDB8'>""" + all_workflows[4] + """</td></tr>"""
        elif all_workflows[4] == 'failed':
            today_all_data += """<td width='25%' style='background-color:#F67280'>""" + all_workflows[4] + """</td></tr>"""
        else:
            today_all_data += """<td width='25%' style='background-color:#FFCE44'>""" + all_workflows[4] + """</td></tr>"""

    send_email(hour_counts_data, total_cnt, workflow_details, total_success_cnt, total_failed_cnt, total_running_cnt, total_other_cnt, failed_incs_data, today_all_data)


def workflow_incident_details(stackstorm_ip_port, api_key, workflow_id):
    incident_id = "0"
    try:
        workflow_url = "http://" + stackstorm_ip_port + "/v1/executions/" + workflow_id + "?st2-api-key=" + api_key
        execution_run = requests.request('GET', workflow_url)
        workflow_output = execution_run.json()
        incident_id = workflow_output['trigger_instance']['payload']['inc_number']
    except Exception as e:
        incident_id = 'N/A'
    return incident_id

def get_current_time_zones():
    est_date = datetime.now().replace(microsecond=0)
    utc_date = est_date + timedelta(hours=5, minutes=0)
    ist_date = est_date + timedelta(hours=10, minutes=30)
    timezones_data = """"<tr align='center'><td width='50%'>Account Name</td><td width='50%'>""" + company + """</td></tr>
                         <tr align='center'><td width='50%'>Server IP</td><td width='50%'>""" + server_ip + """</td></tr>
                         <tr align='center'><td width='50%'>Server Timestamp (EST)</td><td width='50%'>""" + str(est_date) + """</td></tr>
                         <tr align='center'><td width='50%'>UTC Timestamp</td><td width='50%'>""" + str(utc_date) + """</td></tr>
                         <tr align='center'><td width='50%'>IST Timestamp</td><td width='50%'>""" +  str(ist_date) + """</td></tr>"""
    return timezones_data

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

def send_email(hour_counts_data, total, workflow_details, total_success_cnt, total_failed_cnt, total_running_cnt, total_other_cnt, failed_incs_data, today_all_data):
    port = '25'
    smtp_server = '155.16.123.161'
    msg_subject = company_abbreviation + '-STACKSTORM - Hour wise workflows execution trend'
    msg_from = 'noreply@nttdata.com'
    send_mail_sts = (False, 'NONE')
    msg_body_data = "Test line 1"
    message = MIMEMultipart(msg_body_data)
    message['To'] = email.utils.formataddr(('Recipient', msg_to))
    message['From'] = email.utils.formataddr(('Stackstorm', msg_from))
    message['Subject'] = msg_subject
    html_data = """<html>
    <head>
      <style>
        table, th, td {
        border: 1px solid black;
        border-collapse: collapse;
         }
        tr, td {
            align: center;
        }
        tr:nth-child(even) {
            background-color: #E0FFFF;
        }
      </style>
    </head>
    <body>
      <table width='75%' border=1>
      <tr>
         <th colspan='5' style='background-color:#800080'><font color='#FFA500'>SUMMARY</font></th>
      </tr>
      <tr>
         <th style='background-color:#C3FDB8'>SUCCEEDED</th>
         <th style='background-color:#F98B88'>FAILED</th>
         <th style='background-color:#FFCE44'>RUNNING</th>
         <th style='background-color:#9AFEFF'>OTHERS</th>
         <th style='background-color:#FF77FF'>TOTAL</th>
      </tr>
      <tr align='center'>
         <td width='20%' style='background-color:#C3FDB8'>"""+ str(total_success_cnt) + """</td>
         <td width='20%' style='background-color:#F98B88'>"""+ str(total_failed_cnt) + """</td>
         <td width='20%' style='background-color:#FFCE44'>"""+ str(total_running_cnt) + """</td>
         <td width='20%' style='background-color:#9AFEFF'>"""+ str(total_other_cnt) + """</td>
         <td width='20%' style='background-color:#FF77FF'>"""+ str(total_success_cnt + total_failed_cnt + total_running_cnt + total_other_cnt) + """</td>
      </tr>
      </table>
      <br>

      <table width='75%' border=1>
      <tr>
         <th colspan='2' style='background-color:#800080'><font color='#FFA500'>ACCOUNT DETAILS</font></th>
       </tr>
      """ + get_current_time_zones() + """
      <!-- </table> -->
      <!-- <table width='75%' border=1> -->
      <tr>
         <th colspan='2' style='background-color:#800080'><font color='#FFFFFF'>Note: Below hour wise workflows execution trend as per UTC timestamp</font></th>
      </tr>
      <tr>
         <th colspan='2' style='background-color:#800080'><font color='#FFA500'>STACKSTORM - WORKFLOWS HOUR WISE TREND</font></th>
      </tr>""" + hour_counts_data + """
      <tr align='center' style='background-color:#FF77FF'>
         <td width='50%'><b>Total</b></td>
         <td width='50%'><b>"""+ str(total) + """</b></td>
      </tr>
     </table>

     <p>** - Present hour</p>
    <table width='75%' border=1>
     <tr>
       <th colspan='3' style='background-color:#800080'><font color='#FFA500'>WORKFLOWS SUMMARY</font></th>
     </tr>""" + workflow_details + """
    </table>

    <br>
    <table width='75%' border=1>
      <tr>
         <th colspan='4' style='background-color:#800080'><font color='#FFA500'>FAILED INCIDENTS DETAILS</font></th>
      </tr>
      <tr>
         <th style='background-color:#800080'><font color='#FFA500'>Workflow name</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Automation job id</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Incident id</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Status</font></th>
      </tr>""" + failed_incs_data + """
    </table>

    <br>
    <table width='85%' border=1>
      <tr>
         <th colspan='5' style='background-color:#800080'><font color='#FFA500'>ALL WORKFLOWS DETAILS</font></th>
      </tr>
      <tr>
         <th style='background-color:#800080'><font color='#FFA500'>Start time (UTC)</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Automation job id</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Workflow name</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Incident id</font></th>
         <th style='background-color:#800080'><font color='#FFA500'>Status</font></th>
      </tr>""" + today_all_data + """
    </table>

    </body>
    </html>"""
    msg_type = MIMEText(html_data, "html")
    message.attach(msg_type)
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.set_debuglevel(False)
        server.sendmail(msg_from, [msg_to], message.as_string())
        send_mail_sts = (True, 'MAIL_SENT_SUCCESSFULLY')
        server.quit()
        #logging.info("MAIL_SENT_SUCCESSFULLY to %s at %s\n" %(msg_to, "test"))
        print("Mail sent successfully")
    except Exception as e:
        #logging.error("ERROR_SENDING_MAIL: %s" %e)
        #logging.exception("EXCEPTION WHILE SENDING MAIL", exc_info=True)
        send_mail_sts = (False, ('ERROR_SENDING_MAIL', e))
        print("ERROR_SENDING_MAIL: %s" %e)
    return send_mail_sts

if __name__ == '__main__':
        limit = "5000"
        start_time_gt = str(date.today()) + 'T00:00:00.000Z'
        #start_time_gt = time_gt.replace(' ', 'T') + ".000Z"
        #end_time_lt = time_lt.replace(' ', 'T') + ".000Z"
        end_time_lt = str(date.today()) + 'T23:59:59.000Z'

        fetch_execution_job_ids(limit, start_time_gt, end_time_lt)
