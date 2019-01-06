import csv
import time
from datetime import date
from zabbix_api import ZabbixAPI
from datetime import datetime, timedelta
from calendar import timegm
import calendar
from pytz import timezone
import pytz
from dateutil import relativedelta
import urllib2
from urllib2 import URLError



# Catch the first month's day. Script will run in crontab on the first day of the month
date = datetime.now()
print "Report from {}".format(date)
#Catch the last day of previous month
lastday_month = (date - timedelta(days=1)).day
print "last"
print (lastday_month)

meses = ["Janeiro","Fevereiro","Marco","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
monthN = int((date - timedelta(days=1)).month) 
year = int(date.year)
#If is the last month report, catches the previous year since the script will be running on crontab on the first day of the year
if(monthN == 12):
   year = year -1
print year

#Set the first day of the month and hour
month = meses[monthN-1]
dayI = int(1)
hourI = int(0)
minI = int(0)
secI = int(0)

#Set the last day of the month and hour
dayF = int(lastday_month)
hourF = int(23)
minF = int(59)
secF = int(59)
print "Report from {}".format(month)
print "Running at {}".format(date)

# User and password for acessing Zabbix API
username = "username"
password = "password"

# Variable to store Zabbix API Object
zapi = 0 

# Variable to store Zabbix Servix
services = 0

# List to store zabbix services (Name,SLA,Mounth,Parent Service,Mounth_Number)
output = []

# List to store Zabbix Events
incidents = []

#List of trigger Priorities
triggerPriority = ["Not classified","Information","Warning","Average","High","Disaster"]
#List of trigger status
#triggerStatus =["RESOLVED","PROBLEM"]

def get_month_lastday(date):
    """
    Returns the month's last day
    """
    last_day = date.replace(day = calendar.monthrange(date.year, date.month)[1]).day
    return last_day

def unix_time(dttm=None):
  
    """
    #Returns unix timestamp from a Datetime
    # Note: if you pass in a naive dttm object it's assumed to already be in UTC
    # Set your proper Time Zone

    """
    if dttm is None:
       dttm = datetime.utcnow()

    #Set the proper TimeZone!
    dttm = pytz.timezone('America/Sao_Paulo').localize(dttm)
    
    return timegm(dttm.utctimetuple())

def getZabbixAPI():
    
    """
    Get Zabbix API and do the login
    """
    zxapi = ZabbixAPI(server="https://monitoramento.tesouro.gov.br/zabbix")
    zxapi.login(username,password)
    
    return zxapi

def getZabbixServices(zapi):
    
    """
    Catch all IT Services
    """
    services = zapi.service.get(
            {"output": "extend",
             "selectParent":"extend"
             }) 
    
    return services

def getServicesSLAsList(zapi,services):
    
    """
       Get the SLAs from all services in services from initial date (iniDate)
       to final date (finDate). The month's first day to month's last day (global variables)
    """


    iniDate = unix_time(datetime(year,monthN,dayI,hourI,minI,secI))
    finDate = unix_time(datetime(year,monthN,dayF,hourF,minF,secF))
    #print ("nome,sla,mes,ano,local,num")
    for x in services:
        srv = zapi.service.getsla(
                {"serviceids":x['serviceid'],
                  "intervals": [{"from": iniDate,"to": finDate}]
                 })
        #Catch the list with the dictionary containing a service's SLA
        aux = srv[x['serviceid']]['sla'] 
        if len(aux) > 0:
            aux2 = aux[0] #Cathes the SLA value
            output.append([x['name'],int(float(aux2['sla'])*100),month,year,x['parent']['name'],monthN])
       
def writeServicesSLAsList():

    """
    Append the service's SLAs of a specific month stored in the global variable output in 
    an .csv file
    """
    with open('Disponibilidade.csv', mode='a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for o in output:
            print o
            writer.writerow([o[0].encode("utf-8"),
                             o[1],
                             o[2],
                             o[3],
                             o[4].encode("utf-8"),
                             o[5],
                            ])

def formatAck(ack):

    """
    Auxiliary function to format Acknowledges history 
    """
    ack_r = ""
    if(len(ack)>0):
        ack_r = "Time: " + time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(int(ack[0]['clock']))) + " User: "+ack[0]['name']+" "+ack[0]['surname']+" "+"("+ack[0]['alias']+") "+"Message: "+ack[0]['message'] 
        
    return ack_r

def formatDuration(iniTime,finTime):

    """
    Auxiliary function to calculate and format problem duration
    """
    duration_r = ""

    difference = relativedelta.relativedelta(datetime.fromtimestamp(int(finTime)),datetime.fromtimestamp(int(iniTime)))
    months = difference.months
    days = difference.days
    hours = difference.hours
    minutes = difference.minutes
    seconds = difference.seconds
    #print "Difference is  %s months, %s days, %s hours, %s minutes, %s seconds " %(months, days, hours, minutes,seconds)
    duration_r = "%sm %sd %sh %sm %ss" %(months,days,hours,minutes,seconds)
    return duration_r


def getTrigger(zapi,objectID,iniDate,finDate):

  
    """
    Function to get the for a specific event in a specific date (iniDate to finDate)
    """
    
    trigger = zapi.trigger.get(
                {"output": ["priority","status","description","value","expression"],
                "triggerids": objectID,
                "time_from": iniDate,
                "time_till": finDate,
                "expandDescription": 1,
                "expandExpression": 1
                
                })

    return trigger

def getRecoveryEvent(zapi,reventid):

    """
    Function to get the recovery event from the original event (incident generated by a trigger) 
    """
    events_r = zapi.event.get(
                {"output":["eventid","clock"],
                "select_acknowledges": "extend",
                "eventid_from": reventid,
                "eventid_till": reventid,
                "sortfield": ["clock", "eventid"],
                "sortorder": "DESC"
                })

    return events_r

def checkWebScen(trig,web_scs):

    """
    Function to check if a specific web scenario related to a trigger is enabled or disabled
    """
    web_enabled = True
    web_sc_name = ""
    cnt =0
    for w in web_scs:
        if(w['name'] in trig[0]['expression'] and w['status']=='1'):
            web_sc_name = w['name']
            web_enabled = False
            print "web_sc_name false"
            break
            
    return web_enabled

def getWebScen(zapi,hostid):

    """
    Function to get  web scenarios from a specific host
    """
    web_sc = zapi.httptest.get({"output": ["hostid","name","status"],"hostids": hostid, "expandName": 1} )
    return web_sc

def printDiscardedIncident(cnt,e,trig,events_r,websc):

     """
     Auxiliary function for debugging purposes
     The incidentes that has disabled trigger or host or web scenario are not considered by zabbix frontend report nor by this script
     This script considers incidentes without recovery event and with hosts in maintenance (frontend Zabbix 3.4 does not consider hosts in 
     maintenace mode)
     """
     print "######One of the followiong conditions was foud ##################"
     print "trigger or recovery event empty"
     print "trigger or host disabled or"
     print "web scenario disabled"
     print cnt
     print "Events:"
     print e
     print "\n"
     print "Trigger"
     print trig
     print "\n"
     #print "recovery Event:"
     #print events_r  #Aceitando recovery event vazio por enquanto
     print "\n"
     print "Web Scenario:"
     print websc
     print "check web"
     print checkWebScen(trig,websc)
     print "###########################"   


def getZabbixIncidents(zapi):

    """
    This funtion gets a list of Incidents (Events generated by a trigger) from a initial date (iniDate the month's first day)
    to a final date (month's last day).
    For each incident the funtions gets the recovery event (if exists), the scenario web and the trigger to check if the incident
    has to be in the report or no.

    """



    iniDate = unix_time(datetime(year,monthN,dayI,hourI,minI,secI))
    finDate = unix_time(datetime(year,monthN,dayF,hourF,minF,secF))

    print "IniFin"
    print iniDate
    print finDate
    events = zapi.event.get({
        "output": ["eventid","acknowlwdges","clock","objectid","r_eventid","hosts"],
        "time_from": iniDate,
        "time_till": finDate,
        "select_acknowledges": ["surname","name","clock","alias","message"],
        "select_tags": "extend",
        "object": 0, #Generated by a trigger
        "source": 0,
        "value": 1, # Problem Events
        "selectHosts":["hostid","name","status","maintenance_status"],
        "sortfield": ["clock", "eventid"],
        "sortorder": "ASC"
     })
    cnt = 0
    
    for e in events:
        print cnt    
        iniTime = ""
        finTime = ""
        durTime = ""
        trigSatus = ""
        trig = getTrigger(zapi,e['objectid'],iniDate,finDate) 
     
        events_r = getRecoveryEvent(zapi,e['r_eventid'])
        web_scen = getWebScen(zapi,e['hosts'][0]['hostid'])

        #Check if trigger is enabled, if trigger is not empty and if trigger is enabled and if host is not empty and is enabled
        # and check if web_scenario is empty or if not empty if is enabled

        if(len(trig) > 0 and trig[0]['status']=="0" and (len(e['hosts'])>0 and e['hosts'][0]['status']=='0') and (not("web.test.fail" in trig[0]['expression']) or checkWebScen(trig,web_scen))): 
                
            iniTime = time.strftime("%m-%d-%Y  %H:%M:%S", time.localtime(int(e['clock'])))
            if(len(events_r)>0):
                finTime = time.strftime("%m-%d-%Y  %H:%M:%S", time.localtime(int(events_r[0]['clock'])))
                trigStatus = "RESOLVED"
            else:
                #If there is no recovery event the incident was not solved and the trigger is still alarming
                trigStatus = "PROBLEM"

            #Append the incident into the list oof incidents
            incidents.append([triggerPriority[int(trig[0]['priority'])],
                              iniTime,
                              finTime,
                              trigStatus,
                              e['hosts'][0]['name'],
                              trig[0]['description'],
                              durTime,
                              formatAck(e['acknowledges']),
                              "", #Actions
                              ""  #Tags
                              ])
        else:
            # Debugging of discarded incidents
            printDiscardedIncident(cnt,e,trig,events_r,web_scen)
        cnt = cnt + 1    

    #Retunrs the size of the incident's list
    return len(incidents)
        

def writeIncidentsList():

    """
    Append the incidents list of a specific month stored in the global variable incidents in 
    an .csv file
    """

    with open('Incidentes_Zabbix.csv', mode='a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for i in incidents:
            writer.writerow([i[0].encode("utf-8"),
                             i[1].encode("utf-8"),
                             i[2].encode("utf-8"),
                             i[3].encode("utf-8"),
                             i[4].encode("utf-8"),
                             i[5].encode("utf-8"),
                             i[6].encode("utf-8"),
                             i[7].encode("utf-8"),
                             i[8].encode("utf-8"),
                             i[9].encode("utf-8")])


def generateReports():

    """
    Main funtion that calls Incidents and Service SLAs functions
    """

    zapi = getZabbixAPI()
    numIncidents = getZabbixIncidents(zapi)
    services= getZabbixServices(zapi)
    getServicesSLAsList(zapi,services)
    writeServicesSLAsList()
    writeIncidentsList()

    print "Number of Incidents: {}".format(numIncidents)
    print "\n"
    print "Finished at {}".format(datetime.now())
    print "\n"


# Call of the main function
generateReports()


#except Exception as e:

#    print e__doc__
#    print e.message
#    print "Generic Final Exception!!!!!!!!!!!"





