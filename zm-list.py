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
    parser.add_argument('--url', type=str, required=True, help='Base ZoneMinder API URL, e.g. https://server/zm/api')
    parser.add_argument('--monitor-id', type=int, help='ZoneMinder MonitorId. Required unless --start-event is used.')
    parser.add_argument('--start-event', type=int, help='First EventId to process. Not required if using --monitor-id.')
    parser.add_argument('--dry-run', action='store_const', const=True, default=False, help='Do not delete events.')
    args = parser.parse_args()
    if args.monitor_id is None and args.start_event is None:
        parser.error("Either --monitor-id or --start-event is required.")
    return args

if __name__ == "__main__":
    args = parse_args()
    zma = ZmApi(args.url)
    zmf = ZmFiles("/var/lib/zoneminder", zma)
    rek = RekognitionHelper(size = (800,800))

    if args.start_event:
        event_id = args.start_event
    else:
        monitor_index = zma.get_index(monitor_id = args.monitor_id)
        event_id = monitor_index['events'][0]['Event']['Id']

    while event_id:
        delete = True
        event = zma.get_event(event_id)['event']['Event']
        print("%(Id)s - %(StartTime)s - %(Frames)-6s" % event)
        frames = zmf.frames(event = event)
        for frame in frames:
            labels = rek.get_labels(frame)
            labels_names = ",".join([label['Name'] for label in labels['labels']]) or "-"

            if labels['mode'] == 'rekognition':
                print("    %s  %s" % (frame, labels_names), flush = True)
            elif labels['mode'] == 'imagehash':
                print("    # %s   %s (same image hash)" % (frame, labels_names), flush = True)
            if labels['labels']:
                delete = False
                print("    # skipping further checks")
                break
        if delete:
            if not args.dry_run:
                print("DELETING %(Id)s" % event)
                zma.delete_event("%(Id)s" % event)
            else:
                print("DELETING %(Id)s [dry-run]" % event)
        else:
            print("RETAINING %(Id)s" % event)
        print()
        event_id = event['NextOfMonitor']
