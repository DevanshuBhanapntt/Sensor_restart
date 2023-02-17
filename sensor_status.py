#!/usr/bin/env python
import subprocess
import requests
import time
import os
import socket
import logging
from datetime import datetime, timedelta
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

company = "COMPANY_NAME"
company_abbreviation = "COMPANY_ABBREVIATION"
msg_to = "BAO_Offshore_team@nttdata.com"
#msg_to = 'Venkatanagababu.Battina@nttdata.com'
sensor_counter_file =  "/tmp/.sensor_counter.txt"

def register_sensor_list():
    registered_sensors = []
    #If below api key is not working create a new api key by using below command
    #st2 apikey create -k -m '{"test_key": "test api key"}'
    api_key = "API_KEY"
    sensor_parameters = "ref,pack,name,enabled"
    stackstorm_ip_port = "127.0.0.1:9101"
    sensor_url = "http://"+ stackstorm_ip_port + "/v1/sensortypes?st2-api-key=" + api_key + "&include_attributes=" + sensor_parameters
    try:
        sensor_output = (requests.request('GET', sensor_url)).json()
    except Exception as e:
        print("Exception while fetchig data from sensor api. Error is: {}".format(e))
        sensor_output = []
    if isinstance(sensor_output, list):
        for item in sensor_output:
            if item['enabled']:
                registered_sensors.append(item['name'])
    else:
        registered_sensors.append(sensor_output)
    sensor_process = compare_active_sensors()
    logging.info("Enabled sensors are: {}".format(set(registered_sensors)))
    logging.info("Sensor processes running: {}".format(set(sensor_process)))
    if set(registered_sensors) == set(sensor_process):
        logging.info("All sensors are working fine at: %s" %(str(current_date())))
    else:
        try:
            sensors_stopped = set(registered_sensors) - set(sensor_process)
        except Exception as e:
            sensors_stopped = 'ERROR'
        logging.info("================================================================")
        logging.warning("No of registered sensors are %d at %s. %s" %(len(registered_sensors), current_date(), str(registered_sensors)))
        logging.warning("No of sensor processes running are %d at %s. %s" %(len(sensor_process), current_date(), str(sensor_process)))
        logging.info("Restarting sensor services...please wait")
        restart_sensor_service(registered_sensors, sensor_process, current_date(), sensors_stopped)
        logging.info("Restarting sensor services done.")

def compare_active_sensors():
    sensor_name = ""
    sensor_process_list = []
    process_list = subprocess.Popen(['ps', '-ef'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    execute_sensors_command = subprocess.Popen(['grep', 'sensor'], stdin=process_list.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sensors_processes = execute_sensors_command.stdout.readlines()
    for item in sensors_processes:
        decoded_process_output = item.decode('utf-8')
        if '--class-name' in decoded_process_output:
            sensor_name = decoded_process_output.strip().split('--class-name=')[1].split()[0]
            sensor_process_list.append(sensor_name)
    return sensor_process_list

def restart_sensor_service(register_sensors, sensor_processed, sensor_datetime, sensors_stopped):
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
    logging.info("Register sensors: %d" %(len(register_sensors)))
    logging.info("Sensor process:  %d" %(len(sensor_processed)))
    logging.info("Datetime:  %s" %sensor_datetime)
    logging.info("Restart count:  %d" %get_restart_cnt)
    logging.info("Restart status:  %s" %restart_sts)
    logging.info("Services length:  %d" %(len(services_list)))
    logging.info("---------------------------------")
    send_email(str(len(register_sensors)), str(len(sensor_processed)), str(sensor_datetime), str(get_restart_cnt), restart_sts, str(int(len(services_list) + 1)), services_format_data, sensors_stopped)

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

def update_sensor_counter():
    sensor_counter = get_sensor_restart_counter(sensor_counter_file)
    try:
        with open(sensor_counter_file, "w+") as update_counter:
            update_counter.write(str(int(sensor_counter) + 1))
    except Exception as e:
        logging.error("Unable to write to file. File is: %s" %sensor_counter_file)
        logging.exception("UNABLE_TO_CREATE_FILE", exc_info=True)

def send_email(register_sensors, sensor_processed, sensor_datetime, get_restart_cnt, restart_sts, number_of_services, services_format_data, sensors_stopped):
    sensors_stopped_data = str(sensors_stopped).replace('{', '').replace('}', '').replace("'", "")
    port = '25'
    smtp_server = '155.16.123.161'
    msg_subject = company_abbreviation + '-STACKSTORM - SENSOR SERVICES RESTART NOTIFICATION'
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
   </style>
  </head>
  <body>
   <table width='75%' border=1>
     <tr>
     <th colspan='2' style='background-color:#12AD2B'>STACKSTORM - SENSOR ISSUE</th>
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
       <td width='40%'>Date</td>
       <td width='60%'>""" + sensor_datetime + """</td>
    </tr>
    <tr align='center'>
       <td width='40%'>Status</td>
       <td width='60%'>""" + restart_sts + """</td>
    </tr>
    <tr align='center'>
       <td width='40%'>Registered sensors</td>
       <td width='60%'>""" + register_sensors + """</td>
    </tr>
    <tr align='center'>
       <td width='40%'>Sensor processes running</td>
       <td width='60%'>""" + sensor_processed + """</td>
    </tr>
    <tr align='center'>
       <td width='40%'>Stopped sensor(s)</td>
       <td width='60%'>""" + sensors_stopped_data + """</td>
    </tr>
    <tr align='center'>
        <td width='40%'>No of times sensor restarted (on """ + sensor_datetime.split()[0].strip() +""")</td>
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
</html>
"""
    msg_type = MIMEText(html_data, "html")
    message.attach(msg_type)
    server = smtplib.SMTP(smtp_server, port)
    server.set_debuglevel(False)
    try:
        server.sendmail(msg_from, [msg_to], message.as_string())
        send_mail_sts = (True, 'MAIL_SENT_SUCCESSFULLY')
        logging.info("MAIL_SENT_SUCCESSFULLY to %s at %s" %(msg_to, str(current_date())))
    except Exception as e:
        logging.error("ERROR_SENDING_MAIL: %s" %e)
        logging.exception("EXCEPTION WHILE SENDING MAIL", exc_info=True)
        send_mail_sts = (False, ('ERROR_SENDING_MAIL', e))
    finally:
        server.quit()
    return send_mail_sts

def current_date():
    edt_time = datetime.now().replace(microsecond=0)
    change_ist = edt_time + timedelta(hours=9, minutes=30)
    ist_time = str(change_ist) + " IST"
    return ist_time

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
    log_file = "/opt/scripts/logs/sensor_status/"+ current_date().split()[0] +"_sensor_logs.txt"
    log_format = '[%(asctime)s - %(levelname)s - %(funcName)20s(),%(lineno)s] - %(message)s'
    logging.basicConfig(level=logging.INFO, filename=log_file, filemode='a', format=log_format, datefmt='%d-%b-%Y %H:%M:%S')
    logging.info("----S----T----A----T----U----S--------C----H----E----C----K--------S----T----A----R----T----")
    if not mid_hour():
        register_sensor_list()
    else:
        reset_restart_counter()
        logging.info("Resetting the sensor restart counter to zero at %s" %(str(current_date())))
        logging.info("Current time is mid hour. Not checking the sensor status")
    logging.info("----S----T----A----T----U----S--------C----H----E----C----K--------E----N----D----S---------")
