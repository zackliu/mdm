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
MESSAGE_THRESHOLD = 1000.0
CONNECTION_THRESHOLD = 100.0
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

def parseJson(metrics, endpoint):
    result = dict()
    if metrics:
        for item in metrics[endpoint]:
            result[item['HubName']] = {'ConnectionCount' : item['ConnectionCount'], 'MessageCount' : item['MessageCount']}
    return result

 
def smallerOrZero(oldVal, newVal):
    oldVal = int(oldVal)
    newVal = int(newVal)

    if oldVal <= newVal:
        return oldVal

    return 0

def signalr():
    while True:
        metrics = getMetrics()
        clientStart = parseJson(metrics, 'client')
        time.sleep(COLLECT_INTERVAL)
        clientEnd = parseJson(metrics, 'client')
        serverEnd = parseJson(metrics, 'server')
        totalConnection = 0
        totalMessage = 0


        for key in clientEnd:
            newConnectionCount = int(clientEnd[key]['ConnectionCount'])
            newMessageCount = int(clientEnd[key]['MessageCount'])

            sentMetric(NAMESPACE, "ConnectionCount", RESOURCEID, INSTANCEID, newConnectionCount, Hub=key, Endpoint='client')
            totalConnection = totalConnection + newConnectionCount
            sentMetric(NAMESPACE, "MessageCount", RESOURCEID, INSTANCEID, newMessageCount, Hub=key, Endpoint='client')
            totalMessage = totalMessage + newMessageCount

            oldConnectionCount = 0
            oldMessageCount = 0
            if key in clientStart:
                oldConnectionCount = smallerOrZero(clientStart[key]['ConnectionCount'], newConnectionCount)
                oldMessageCount = smallerOrZero(clientStart[key]['MessageCount'], newMessageCount)
            sentMetric(NAMESPACE, "ConnectionCountPerSecond", RESOURCEID, INSTANCEID, getRate(oldConnectionCount, newConnectionCount, COLLECT_INTERVAL))
            sentMetric(NAMESPACE, "MessageCountPerSecond", RESOURCEID, INSTANCEID, getRate(oldMessageCount, newMessageCount, COLLECT_INTERVAL))
        
        sentMetric(NAMESPACE, "ConnectionUsed", RESOURCEID, INSTANCEID, float(totalConnection) / CONNECTION_THRESHOLD)
        sentMetric(NAMESPACE, "MessagUsed", RESOURCEID, INSTANCEID, float(totalMessage) / MESSAGE_THRESHOLD)

        for key in serverEnd:
            newConnectionCount = int(serverEnd[key]['ConnectionCount'])
            newMessageCount = int(serverEnd[key]['MessageCount'])
            sentMetric(NAMESPACE, "ConnectionCount", RESOURCEID, INSTANCEID, newConnectionCount, Hub=key, Endpoint='server')
            sentMetric(NAMESPACE, "MessageCount", RESOURCEID, INSTANCEID, newMessageCount, Hub=key, Endpoint='server')

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


