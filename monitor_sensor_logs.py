#!/usr/bin/env python
from datetime import datetime, timedelta
import logging
import subprocess
import time
import os
import socket
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

company = "TRINITY INDUSTRIES"
company_abbreviation = "TRINITY INDUSTRIES"
#msg_to = "BAO_Offshore_team@nttdata.com"
msg_to = 'venkatanagababu.battina@nttdata.com'
sensor_counter_file = "/tmp/.sensor_stuck_file.txt"
sensor_logs_file_path = "/var/log/st2/st2sensorcontainer.log"

def restart_sensor(total_minutes_value, current_date, latest_logs_date, sensor_type):
    #total_minutes_value, current_date, latest_logs_date = monitor_incident_sensor_logs()
    if total_minutes_value == -1:
        logging.info("Exception while checking date")
    elif total_minutes_value > 2:
        services_list = []
        services_format_data = ""
        execute_restart_cmd = subprocess.Popen(['st2ctl', 'reload', '--register-all'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        sensor_restart_output = execute_restart_cmd.stdout.readlines()
        update_sensor_counter()
        get_restart_cnt = get_sensor_restart_counter(sensor_counter_file)
        cnt = 0
        for item in sensor_restart_output:
            cnt += 1
            decoded_sensor_output = item.strip().decode('utf-8')
            if '##### st2 components status #####' in decoded_sensor_output:
                break
        sensor_pid_data = sensor_restart_output[int(cnt):]
        for sensor_service in sensor_pid_data:
            decoded_sensor_data = sensor_service.strip().decode('utf-8')
            if 'pid' in decoded_sensor_data.lower():
                services_list.append(decoded_sensor_data)
        for item in services_list:
            services_format_data += "<tr><td width='60%' align='center'>" + item + "</td></tr>"
        restart_sts = "Sensor restart failed"
        if len(services_list) > 0:
            restart_sts = "Sensor restarted successfully"
        logging.info("Sensor restart data is: ")
        logging.info("---------------------------------")
        logging.info("Current date is: %s" %current_date)
        logging.info("Sensor logs last updated time is:  %s" %latest_logs_date)
        logging.info("Total time sensor was down:  %s" %(convert_minutes_to_hour(total_minutes_value)))
        logging.info("Restart count:  %d" %get_restart_cnt)
        logging.info("Restart status:  %s" %restart_sts)
        logging.info("Services length:  %d" %(len(services_list)))
        logging.info("---------------------------------")
        send_email(str(current_date), str(latest_logs_date), str(total_minutes_value), str(get_restart_cnt), restart_sts, str(int(len(services_list) + 1)), services_format_data)
        print(restart_sts)
    elif total_minutes_value <= 2:
        logging.info("%s is working fine. Sensor logs last upate at %s minutes back" %(sensor_type, total_minutes_value))
    else:
        logging.warn("Invalid time difference value")

def update_sensor_counter():
    sensor_counter = get_sensor_restart_counter(sensor_counter_file)
    try:
        with open(sensor_counter_file, "w+") as update_counter:
            update_counter.write(str(int(sensor_counter) + 1))
    except Exception as e:
        logging.error("Unable to write to file. File is: %s" %sensor_counter_file)
        logging.exception("UNABLE_TO_CREATE_FILE", exc_info=True)

def get_sensor_restart_counter(sensor_counter_file):
    counter = 0
    if not os.path.exists(sensor_counter_file):
        try:
            with open(sensor_counter_file, "w+") as create_file:
                create_file.write("0")
        except Exception as e:
            logging.error("Unable to create file. File is: %s" %sensor_counter_file)
            logging.exception("UNABLE_TO_CREATE_FILE", exc_info=True)
    try:
        with open(sensor_counter_file, "r+") as restart_counter:
            counter = int(restart_counter.read())
    except Exception as e:
        logging.error("Exception while reading the file: %s" %e)
        logging.exception("Exception while reading the file", exc_info=True)
        counter = 0
    return counter

def read_file_content(serach_str_1, search_str_2, search_regex):
    #search_str_1 = 'STARTED_xxxx_SENSOR_AT:'
    #search_str_2 = 'COMPLETED_xxxx_SENSOR_AT:'
    #search_regex = '_INCIDENT_SENSOR_AT:'
    logs_list = []
    with open(sensor_logs_file_path, "r+") as sensor_logs:
        sensor_data = sensor_logs.readlines()
        for line_no, line in enumerate(sensor_data):
            if serach_str_1 in line.strip() or search_str_2 in line.strip():
                try:
                    data = line.strip().split(search_regex)[1].split('.')[0].strip()
                except Exception as e:
                    data = 'INVALID'
                logs_list.append(data)
    return logs_list


def monitor_sensor_logs(sensor_type):
    if sensor_type == 'INCIDENT_SENSOR':
        logs_list = read_file_content('STARTED_INCIDENT_SENSOR_AT:', 'COMPLETED_INCIDENT_SENSOR_AT:', '_INCIDENT_SENSOR_AT:')
    if sensor_type == 'PENDING_SENSOR':
        logs_list = read_file_content('STARTED_PENDING_SENSOR_AT:', 'COMPLETED_PENDING_SENSOR_AT:', '_PENDING_SENSOR_AT:')

    logs_date_format = datetime.strptime(logs_list[-1], "%Y-%m-%d %H:%M:%S")
    latest_logs_date = convert_to_date(logs_date_format.strftime("%Y-%m-%d %H:%M"))
    current_date = convert_to_date(datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("Current date is: {}".format(current_date))
    print("{}: Latest logs date is: {}".format(sensor_type, latest_logs_date))
    try:
        time_diff = int((current_date - latest_logs_date).total_seconds()/60)
    except Exception as e:
        time_diff = -1
    print("{}: Time difference data is: {}".format(sensor_type, time_diff))
    restart_sensor(time_diff, current_date, latest_logs_date, sensor_type)

def convert_to_date(date_value):
    try:
        date_str = datetime.strptime(date_value, "%Y-%m-%d %H:%M")
    except Exception as e:
        date_str = "INVALID"
    return date_str

def get_server_ip_address():
    hostname = ip_address = ""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
    except Exception as e:
        logging.error("GET_IP_EXCEPTION: %s" %e)
        logging.exception("EXCEPTION WHILE FETCHING SERVER IP", exc_info=True)
        ip_address = "EXCEPTION"
    return ip_address

def send_email(current_date, latest_logs_date, total_minutes_value, get_restart_cnt, restart_sts, number_of_services, services_format_data):
    port = '25'
    smtp_server = '155.16.123.161'
    msg_subject = company_abbreviation + '-STACKSTORM - SENSOR STUCK RESTART NOTIFICATION'
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
         <th colspan='2' style='background-color:#800080'><font color='#FFA500'>STACKSTORM - SENSOR STUCK ISSUE</font></th>
       </tr>
       <tr align='center'>
         <td width='40%'>Company</td>
         <td width='60%'>""" + company + """</td>
       </tr>
       <tr align='center'>
         <td width='40%'>Stackstorm server ip</td>
         <td width='60%'>""" + get_server_ip_address() + """</td>
       </tr>
       <tr align='center'>
         <td width='40%'>Current Date</td>
         <td width='60%'>""" + current_date + timezone() + """</td>
       </tr>
       <tr align='center'>
         <td width='40%'>Sensor logs last updated</td>
         <td width='60%'>""" + latest_logs_date + timezone() + """</td>
       </tr>
       <tr align='center'>
         <td width='40%'>Total time sensor was down</td>
         <td width='60%'>""" + convert_minutes_to_hour(total_minutes_value) + """</td>
       </tr>
       <tr align='center'>
         <td width='40%'>Status</td>
         <td width='60%'>""" + restart_sts + """</td>
       </tr>
       <tr align='center'>
         <td width='40%'>No of times sensor restarted (on """ + current_date.split()[0].strip() +""")</td>
         <td width='60%'>""" + get_restart_cnt + """</td>
       </tr>
       <tr align='center'>
         <td width='40%' rowspan='""" + number_of_services + """'>Sensor services list</td>
       </tr>""" + services_format_data + """
       <tr align='center'>
         <td width='40%'>Message</td>
         <td width='60%'>Please check /var/log/st2/st2sensorcontainer.log file for errors in sensor.</td>
       </tr>
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
        logging.info("MAIL_SENT_SUCCESSFULLY to %s at %s\n" %(msg_to, str(current_date_value())))
    except Exception as e:
        logging.error("ERROR_SENDING_MAIL: %s" %e)
        logging.exception("EXCEPTION WHILE SENDING MAIL", exc_info=True)
        send_mail_sts = (False, ('ERROR_SENDING_MAIL', e))
    return send_mail_sts

def current_date_value():
    edt_time = datetime.now().replace(microsecond=0)
    change_ist = edt_time + timedelta(hours=9, minutes=30)
    ist_time = str(change_ist) + " IST"
    return ist_time

def timezone():
    try:
        current_timezone = datetime.now().astimezone().strftime('%Z')
    except Exception as e:
        current_timezone = ""
    return " " + str(current_timezone)

def convert_minutes_to_hour(total_minutes):
    try:
        hour = int(total_minutes)//60
        minutes = int(total_minutes)%60
    except Exception as e:
        print("Exception is: {}".format(e))
        hour = minutes = "INVALID"
    total_hours = str(hour) + " Hour(s) : " + str(minutes) + " Minute(s) : 0 Seconds"
    return total_hours

def reset_restart_counter():
    counter = 0
    if os.path.exists(sensor_counter_file):
        try:
            with open(sensor_counter_file, "w+") as create_file:
                create_file.write("0")
        except Exception as e:
            logging.error("Unable to create file. File is: %s" %sensor_counter_file)
            logging.exception("UNABLE_TO_CREATE_FILE", exc_info=True)

def mid_hour():
    mid_hour_check = False
    hour_data = datetime.now().hour
    minute_data = datetime.now().minute
    if hour_data == 0 and minute_data == 0:
        mid_hour_check = True
    else:
        mid_hour_check = False
    return mid_hour_check

if __name__ == "__main__":
    log_file = "/opt/scripts/logs/sensor_stuck_data/"+ current_date_value().split()[0] +"_sensor_logs.txt"
    log_format = '[%(asctime)s - %(levelname)s - %(funcName)20s(),%(lineno)s] - %(message)s'
    logging.basicConfig(level=logging.INFO, filename=log_file, filemode='a', format=log_format, datefmt='%d-%b-%Y %H:%M:%S')
    if not mid_hour():
        monitor_sensor_logs('INCIDENT_SENSOR')
        monitor_sensor_logs('PENDING_SENSOR')
    else:
        reset_restart_counter()
        logging.info("Resetting the sensor stuck counter to zero at %s" %(str(current_date())))
        logging.info("Current time is mid hour. Not checking the sensor logs")
