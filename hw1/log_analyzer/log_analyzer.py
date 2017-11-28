#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


import os
import glob
import json
import re
import logging
from decimal import Decimal
from collections import defaultdict


logger = logging.getLogger()
logger.setLevel(logging.INFO)


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


class Parser:

    def __init__(self):
        self.pattern = re.compile(
            r'(?P<remote_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s'
            r'(?P<remote_user>\S+)\s+'
            r'(?P<http_x_real_ip>\S+)\s+'
            r'\[(?P<time_local>.+)\]\s+'
            r'"(?P<request>.*?)"\s+'
            r'(?P<status>\d{3})\s+'
            '(?P<body_bytes_sent>\d+)\s+'
            r'"(?P<http_referer>.+)"\s+'
            r'"(?P<http_user_agent>.+)"\s+'
            r'"(?P<http_x_forwarded_for>.+)"\s+'
            r'"(?P<http_X_REQUEST_ID>.+)"\s+'
            r'"(?P<http_X_RB_USER>.+)"\s+'
            r'(?P<request_time>.+)'
        )

    def _parse_url(self, request):
        try:
            return request.split(' ')[1]
        except IndexError:
            return request

    def _parse_request_time(self, request_time):
        return float(request_time)

    def parse(self, log_entry):
        result = re.match(self.pattern, log_entry)
        result = result.groupdict() if result is not None else {}
        return (
            self._parse_url(result.get('request')),
            self._parse_request_time(result.get('request_time'))
        )
        

class UrlsReport:

    def __init__(self, ndigits=2):
        self.entries = defaultdict(lambda: defaultdict(lambda: 0))
        self.ndigits = ndigits

        self._count_requests = 0
        self._all_requests_time = 0

    def _get_percent(self, total, value):
        return round(value / (total / 100), self.ndigits)

    def _get_mid(self, total, count):
        return round(total / count, self.ndigits)

    def add(self, url, request_time):
        self._count_requests += 1
        self._all_requests_time = round(
            self._all_requests_time + request_time,
            self.ndigits
        )

        if url not in self.entries:
            self.entries[url]['url'] = url

            # Creates the lazy fields if the url is not in entries
            self.entries[url]['count_perc'] = lambda: self._get_percent(
                self._count_requests, self.entries[url]['count']
            )
            self.entries[url]['time_perc'] = lambda: self._get_percent(
                self._all_requests_time, self.entries[url]['time_sum'],
            )
            self.entries[url]['time_avg'] = lambda: self._get_mid(
                self.entries[url]['time_sum'], self.entries[url]['count']
            )

        self.entries[url]['count'] += 1
        self.entries[url]['time_sum'] = round(
            self.entries[url]['time_sum'] + request_time,
            self.ndigits
        )
        if Decimal(request_time) > Decimal(self.entries[url]['time_max']):
            self.entries[url]['time_max'] = request_time

    def to_json(self, report_size):
        return json.dumps(
            sorted(
                self.entries.values(), key=lambda entry: - entry['time_sum']
            )[:report_size],
            default=lambda lazy_object: lazy_object()
        )

    def save(self, report_path, report_size):
        with open('./templates/report.html', 'r', encoding='utf-8') as f:
            template = f.read()
            
        template = template.replace('$table_json', self.to_json(report_size))
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(template)


class LogAnalyzer:

    def __init__(self, parser=None, report=None):
        self.parser = parser if parser is not None else Parser()
        self.report = report if report is not None else UrlsReport()

    def scan_dir(self, logs_dir):
        log_files = glob.glob(os.path.join(logs_dir, 'nginx-access-ui*'))
        try:
            return max(log_files, key=lambda file: os.stat(file).st_mtime)
        except ValueError:
            return
        
    def get_report_name(self, log):
        re_time = re.compile(r'(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})')
        log_time = re_time.search(log).groupdict()
        return 'report-{Y}.{m}.{d}.html'.format(**log_time)

    def create_report(self, logs_dir, report_dir, report_size):
        if os.path.exists(logs_dir):
            log = self.scan_dir(logs_dir)
            if log is None:
                return
            
            report_name = self.get_report_name(log)
            if not os.path.exists(os.path.join(report_dir, report_name)):
                with open(log, 'r', encoding='utf-8') as f:
                    for url, r_time in (self.parser.parse(line) for line in f):
                        if url is not None and r_time is not None:
                            self.report.add(url, r_time)
                        else:
                            return
                        
                self.report.save(os.path.join(report_dir, report_name),
                                 report_size)

def main():
    pass

if __name__ == "__main__":

    LOG_DIR = '.'
    REPORT_DIR = '.'

    r = LogAnalyzer()
    r.create_report('.', '.', 1000)