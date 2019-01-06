
FROM python:2.7

run apt-get update && apt-get install -y cron vim && apt-get clean 
run pip install zabbix-api pytz python-dateutil
RUN mkdir /code
WORKDIR /code
#run apt-get install -y python python-pip && apt-get clean && pip install openpyxl zabbix-api pytz python-dateutil
ENV EDITOR=vim
ENTRYPOINT /bin/bash
LABEL Description="Microservico Zabbix"

