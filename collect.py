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
# RESOURCEID = 'resourceid'
# INSTANCEID = 'instanceid'

# NOTE: write_mdm_statsd JSON payloads must have '{' as *first* character, otherwise the module won't recognize it!

def getMetrics():
    url = 'http://localhost:5001/health'
    r = requests.get(url)
    if r.status_code != 200:
        logging.warning('Get ' + url + ' failed')
        return None
    return json.loads(r.text)
    
def sentMetric(namespace, metricName, resourceId, instanceId, value, **kw):
    metricObj = {'Namespace': namespace, 'Metric': metricName, 'Dims': {'ResourceId': resourceId, 'InstanceId': instanceId}}
    for key in kw:
        metricObj['Dims'][key] = kw[key]
    metricString = json.dumps(metricObj)
    # print metricString + str(value)
    logging.info(metricString + str(value))
    metric.gauge(metricString, value)
 

def signalr():
    while True:
        metrics = getMetrics()

        if metrics != None:
            for item in metrics['client']:
                sentMetric(NAMESPACE, 'ClientCurrentConnection', RESOURCEID, INSTANCEID, item['ConnectionCount'], Hub=item['HubName'])
                sentMetric(NAMESPACE, 'ClientMessageCount', RESOURCEID, INSTANCEID, item['MessageCount'], Hub=item['HubName'])
            for item in metrics['server']:
                sentMetric(NAMESPACE, 'ServerCurrentConnection', RESOURCEID, INSTANCEID, item['ConnectionCount'], Hub=item['HubName'])
                sentMetric(NAMESPACE, 'ServerMessageCount', RESOURCEID, INSTANCEID, item['MessageCount'], Hub=item['HubName'])

        time.sleep(COLLECT_INTERVAL)
        


def getRate(startVal, endVal, interval=1):
    return (endVal - startVal) / interval

def disk():
    while True:
        diskIoStart = psutil.disk_io_counters()
        time.sleep(COLLECT_INTERVAL)
        diskIoEnd = psutil.disk_io_counters()

        sentMetric(NAMESPACE, 'Disk Read Bytes/Sec', RESOURCEID, INSTANCEID, getRate(diskIoStart.read_bytes, diskIoEnd.read_bytes, COLLECT_INTERVAL))
        sentMetric(NAMESPACE, 'Disk Write Bytes/Sec', RESOURCEID, INSTANCEID, getRate(diskIoStart.write_bytes, diskIoEnd.write_bytes, COLLECT_INTERVAL))
        sentMetric(NAMESPACE, 'Disk Read Operations/Sec', RESOURCEID, INSTANCEID, getRate(diskIoStart.read_count, diskIoEnd.read_count, COLLECT_INTERVAL))
        sentMetric(NAMESPACE, 'Disk Write Operations/Sec', RESOURCEID, INSTANCEID, getRate(diskIoStart.write_count, diskIoEnd.write_count, COLLECT_INTERVAL))


def network():
    while True:
        networkStart = psutil.net_io_counters()
        time.sleep(COLLECT_INTERVAL)
        networkEnd = psutil.net_io_counters()

        sentMetric(NAMESPACE, 'Network In', RESOURCEID, INSTANCEID, getRate(networkStart.bytes_recv, networkEnd.bytes_recv))
        sentMetric(NAMESPACE, 'Network Out', RESOURCEID, INSTANCEID, getRate(networkStart.bytes_sent, networkEnd.bytes_sent))

def cpu():
    while True:
        sentMetric(NAMESPACE, 'Percentage CPU', RESOURCEID, INSTANCEID, psutil.cpu_percent(10))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename='/var/log/collector.log', filemode='w', format='%(asctime)s - %(filename)s - %(levelname)s: %(message)s')
    multiprocessing.Process(target=signalr).start()
    multiprocessing.Process(target=disk).start()
    multiprocessing.Process(target=network).start()
    multiprocessing.Process(target=cpu).start()


