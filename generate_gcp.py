import requests
import time
import json
import logging
import config
import wgs2gcj02

logging.basicConfig(level=logging.DEBUG)


def generate_gcp_origin(interval):
    min_x = config.china_extent['min_lng'] + 0.0
    min_y = config.china_extent['min_lat'] + 0.0
    max_x = config.china_extent['max_lng'] + 0.0
    max_y = config.china_extent['max_lat'] + 0.0
    
    interval += 0.0

    gcp_count = int((max_x - min_x) / interval) * int((max_y - min_y) / interval)

    if gcp_count > 400000:
        logging.error('too many control points. choose larger interval please.')
        exit()
    
    if gcp_count < 20:
        logging.error(
            'too little control points. choose smaller interval please.')
        exit()

    logging.info('generate control points number:' + str(gcp_count))
    
    gcps = []
    gcp_x = min_x + interval
    gcp_y = min_y + interval
    while gcp_x < max_x:
        while gcp_y < max_y:
            gcps.append((gcp_x, gcp_y))
            gcp_y += interval

        gcp_y = min_y + interval
        gcp_x += interval
    
    return gcps


def query_gaode(gcps_84):
    req_str = ''
    for i in xrange(0,len(gcps_84)):
        gcp84 = gcps_84[i]
        req_str = req_str + \
            str(round(gcp84[0], 6)) + ',' + \
            str(round(gcp84[1], 6)) + '|'

    req_str = req_str[:-1]
    reqdata = {
        'locations': req_str,
        'coordsys': 'gps',
        'output': 'json',
        'key': config.gaode_key
     }

    r = requests.get(
        'http://restapi.amap.com/v3/assistant/coordinate/convert', params=reqdata)

    r_json = r.json()
    gd_str = r_json['locations']
    gd_array = gd_str.split(';')

    query_result = []
    for i in xrange(0,len(gd_array)):
        gd_x = float(gd_array[i].split(',')[0])
        gd_y = float(gd_array[i].split(',')[1])
        gcp84 = gcps_84[i]
        gcp84_x = gcp84[0]
        gcp84_y = gcp84[1]
        local_trans_y, local_trans_x = wgs2gcj02.transform(
            round(gcp84_y, 6), round(gcp84_x, 6))
        delta_x = gd_x - local_trans_x
        delta_y = gd_y - local_trans_y
        
        values = []
        values.append(round(gcp84_x, 6))
        values.append(round(gcp84_y, 6))
        values.append(gd_x)
        values.append(gd_y)
        values.append(delta_x)
        values.append(delta_y)

        value_str = ','.join(str(x) for x in values) + '\r\n'
        query_result.append(value_str)
    
    return query_result


def generate_gcp_gaode(interval):
    gcps_84 = generate_gcp_origin(interval)

    results = []
    #results.append('wgs_x,wgs_y,gcj_x,gcj_y,delta_x,delta_y')

    step = 40
    start = 0
    while start + step < len(gcps_84):
        query_gcps = gcps_84[start:start+step]
        results += query_gaode(query_gcps)
        start += step
        # geode api QPS limits
        time.sleep(1)

    results += query_gaode(gcps_84[start:len(gcps_84)])



    with open('gcps_gd', 'w') as newfile:
        newfile.writelines(results)
    
    logging.info('finish.')

generate_gcp_gaode(1)
