#!/usr/bin/env python3.6

import os
import glob
import json
import requests
import argparse

from rekognition import RekognitionHelper

class ZmApi():
    def __init__(self, api_base_url):
        self.base = api_base_url

    def get_index(self, monitor_id):
        url = "%s/events/index/MonitorId:%d.json" % (self.base, monitor_id)
        r = requests.get(url, verify=False)
        return json.loads(r.text)

    def get_event(self, event_id):
        url = "%s/events/%s.json" % (self.base, event_id)
        r = requests.get(url, verify=False)
        return json.loads(r.text)

    def delete_event(self, event_id):
        url = "%s/events/%s.json" % (self.base, event_id)
        r = requests.delete(url, verify=False)

class ZmFiles():
    def __init__(self, base_dir, zm_api):
        self.dir = base_dir
        self.zm_api = zm_api

    def frames(self, event = None, event_id = 0, stride = 50):
        frames = []
        if event is None:
            event = self.zm_api.get_event(event_id)
            event = event['event']['Event']
        base_dir = os.path.join(self.dir, event['BasePath'])
        idx = 0
        try:
            dirlist = glob.glob(os.path.join(base_dir, "*-capture.jpg"))
            dirlist.sort()
        except FileNotFoundError:
            return frames
        while True:
            try:
                frames.append(os.path.join(base_dir, dirlist[idx]))
                idx += stride
            except IndexError:
                break
        return frames

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-event', type=int, help='First EventId to process')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    zma = ZmApi("https://172.31.174.9/zm/api")
    zmf = ZmFiles("/var/lib/zoneminder", zma)
    rek = RekognitionHelper(size = (800,800))
    args = parse_args()

    if args.start_event:
        event_id = args.start_event
    else:
        monitor_index = zma.get_index(monitor_id = 4)
        event_id = monitor_index['events'][0]['Event']['Id']

    while event_id:
        delete = True
        event = zma.get_event(event_id)['event']['Event']
        print("%(Id)s - %(StartTime)s - %(Frames)-6s" % event)
        frames = zmf.frames(event = event)
        for frame in frames:
            labels = rek.get_labels(frame)
            labels_names = ",".join([label['Name'] for label in labels])
            print("    %s  %s" % (frame, labels_names or "-"), flush = True)
            if labels:
                delete = False
                print("    # skipping further checks")
                break
        if delete:
            print("DELETING %(Id)s" % event)
            zma.delete_event("%(Id)s" % event)
        else:
            print("RETAINING %(Id)s" % event)
        print()
        event_id = event['NextOfMonitor']