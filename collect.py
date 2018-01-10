#!/usr/bin/env python

import statsd
import time
import random
import requests
import json
import logging
import os
import multiprocessing
import psutil

COLLECT_INTERVAL = 10
NAMESPACE = 'SignalRShoeboxTest'
metric = statsd.StatsClient()
RESOURCEID = os.environ['RESOURCEID']
INSTANCEID = open('/etc/hostname', 'r').read().strip()

# NOTE: write_mdm_statsd JSON payloads must have '{' as *first* character, otherwise the module won't recognize it!

def getMetrics():
    url = 'http://localhost:5001/health'
    r = requests.get(url)
    if r.status_code != 200:
        logging.warning('Get ' + url + ' failed')
        return None
    return json.loads(r.text)
    
# def sentMetric(namespace, metricName, resourceId, instanceId, hubName, value):
#     metricString = '''{
#         "Namespace": "%s",
#         "Metric": "%s",
#         "Dims": {
#             "ResourceId":"%s",
#             "InstanceId":"%s",
#             "HubName":"%s"
#         }
#     }
#     '''.replace('\n', '') % (namespace, metricName, resourceId, instanceId, hubName)
#     logging.info(metricString.replace(' ', ''))
#     metric.gauge(metricString, value)

def sentMetric(namespace, metricName, resourceId, instanceId, value, **kw):
    metricString = '''{
        "Namespace": "%s",
        "Metric": "%s",
        "Dims": {
            "ResourceId":"%s",
            "InstanceId":"%s"'''
    for key in kw:
        metricString + ',"%s":"%s"' % (key, kw[key])

    '''
        }
    }
    '''.replace('\n', '').replace(' ', '') % (namespace, metricName, resourceId, instanceId)
    logging.info(metricString)
    metric.gauge(metricString, value)

def sentMetrics(metrics):
    for item in metrics['client']:
        sentMetric(NAMESPACE, 'ClientCurrentConnection', RESOURCEID, INSTANCEID, item['ConnectionCount'], Hub=item['HubName'])
        sentMetric(NAMESPACE, 'ClientMessageCount', RESOURCEID, INSTANCEID, item['MessageCount'], Hub=item['HubName'])
    for item in metrics['server']:
        sentMetric(NAMESPACE, 'ServerCurrentConnection', RESOURCEID, INSTANCEID, item['ConnectionCount'], Hub=item['HubName'])
        sentMetric(NAMESPACE, 'ServerMessageCount', RESOURCEID, INSTANCEID, item['MessageCount'], Hub=item['HubName'])
    

def signalr():
    while True:
        metrics = getMetrics()
        if metrics == None:
            logging.info('Failed to get metrics')
        else:
            sentMetrics(metrics)
            logging.info('Get metrics successfully')

        time.sleep(COLLECT_INTERVAL)

def disk():
    while True:
        diskIo = psutil.disk_io_counters()
        sentMetric(NAMESPACE, "DiskBytes", RESOURCEID, INSTANCEID, diskIo.read_bytes, Operation='read')
        sentMetric(NAMESPACE, "DiskBytes", RESOURCEID, INSTANCEID, diskIo.write_bytes, Operation='write')




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename='/var/log/collector.log', filemode='w', format='%(asctime)s - %(filename)s - %(levelname)s: %(message)s')
    multiprocessing.Process(target=signalr).start()
    multiprocessing.Process(target=disk).start()
