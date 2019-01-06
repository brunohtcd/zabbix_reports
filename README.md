# zabbix_reports
Script to get Zabbix reports from API using python.
This script calls Zabbiz API to get two reports from Zabbix: 
       - Problems (events caused by trigger) that ocurred in a month 
       - IT Service's avaibility in a month
       
 The script must must be executed on the first day of a month and returns the Problem Report and IT Services' avaiability Report from the previous month. It consideres events from the month's first day from 0h0m0s to the month's last day until 23h59h59s.
 
 A Docker file using a Python:2.7 base was provided in case you want to wrap the code in a container. 
 A crontab file that you can put in /var/cron.d was provided scheduling the script to run on the irst day of each month. You can schedule the script to run in the Zabbix server or another sever.
 The script will append information of both reports in .csv files. You can use the .csv files to build a better visualization of the information using Power BI for example.
 
 PS1: You will need a Zabbix user with access to all Zabbix Hosts. 
 PS2: I'm not a Python specialist.
 
