#!/usr/bin/env python3.6

import os
import glob
import json
import requests
import argparse
import dateparser

from rekognition import RekognitionHelper

class ZmApi():
    def __init__(self, api_base_url):
        self.base = api_base_url

    def get_index(self, monitor_id, start_time = None):
        url = "%s/events/index/MonitorId:%d" % (self.base, monitor_id)
        if start_time:
            url += "/StartTime >=:{}".format(start_time.strftime('%Y-%m-%d %H:%M:%S'))
        url += ".json"
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

class DateTimeArgument():
    def __call__(self, value):
        dt = dateparser.parse(value)
        if not dt:
            raise argparse.ArgumentTypeError('Unable to parse date/time string: {}'.format(value))
        return dt

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, required=True, help='Base ZoneMinder API URL, e.g. https://server/zm/api')
    parser.add_argument('--monitor-id', type=int, required=True, help='ZoneMinder MonitorId.')
    parser.add_argument('--start-event', type=int, help='First EventId to process. Not required if using --start-time.')
    parser.add_argument('--start-time', type=DateTimeArgument(), help='Time stamp of the first event to process. Not required if using --start-event.')
    parser.add_argument('--ignore-labels', type=str, action='append', default=[], help='Ignore listed labels.')
    parser.add_argument('--dry-run', action='store_const', const=True, default=False, help='Do not delete events.')
    args = parser.parse_args()
    if args.start_event is None and args.start_time is None:
        parser.error("Either --start-event or --start-time is required.")
    if args.ignore_labels:
        args.ignore_labels = ",".join(args.ignore_labels).split(",")
    return args

if __name__ == "__main__":
    args = parse_args()
    zma = ZmApi(args.url)
    zmf = ZmFiles("/var/lib/zoneminder", zma)
    rek = RekognitionHelper(size = (800,800))

    if args.start_event:
        event_id = args.start_event
    elif args.start_time:
        monitor_index = zma.get_index(monitor_id = args.monitor_id, start_time = args.start_time)
        event_id = monitor_index['events'][0]['Event']['Id']
    else:
        monitor_index = zma.get_index(monitor_id = args.monitor_id)
        event_id = monitor_index['events'][0]['Event']['Id']

    while event_id:
        delete = True
        event = zma.get_event(event_id)['event']['Event']
        print("%(Id)s - %(StartTime)s - %(Frames)-6s" % event)
        frames = zmf.frames(event = event)
        for frame in frames:
            try:
                labels = rek.get_labels(frame, ignore_labels = args.ignore_labels)
            except Exception as e:
                print("    # %s   - (%s)" % (frame, str(e)), flush = True)
                continue

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
