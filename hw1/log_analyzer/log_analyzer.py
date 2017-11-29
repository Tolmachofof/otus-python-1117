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
import gzip
import statistics
from decimal import Decimal
from collections import defaultdict
from functools import wraps


__all__ = ('Parser', 'UrlsReport', 'LogAnalyzer')


def log_it(level):
    def deco(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                logging.log(level, "Started: {}.".format(fn.__name__))
                result = fn(*args, **kwargs)
                logging.log(level, "Finished: {}.".format(fn.__name__))
                return result
            except Exception as exc:
                logging.exception("Error in {}".format(fn.__name__))
                raise exc
        return wrapper
    return deco


class Median:

    def __init__(self, items=None, ndigits=2):
        self.items = items if items is not None else []
        self.ndigits = ndigits

    def add(self, item):
        self.items.append(item)

    def __call__(self):
        return round(statistics.median(self.items), self.ndigits)


class Parser:

    def __init__(self):
        self.pattern = re.compile(
            r'(?P<remote_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s'
            r'(?P<remote_user>\S+)\s+'
            r'(?P<http_x_real_ip>\S+)\s+'
            r'\[(?P<time_local>.+)\]\s+'
            r'"(?P<request>.*?)"\s+'
            r'(?P<status>\d{3})\s+'
            r'(?P<body_bytes_sent>\d+)\s+'
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
        except (IndexError, AttributeError):
            logging.error('Can not parse url: {}.'.format(request))
            return request

    def _parse_request_time(self, request_time):
        try:
            return float(request_time)
        except TypeError:
            logging.error(
                'Can not convert {} to request time.'.format(request_time)
            )
            return float(0)

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
            self.entries[url]['time_med'] = Median(ndigits=self.ndigits)

        self.entries[url]['count'] += 1
        self.entries[url]['time_sum'] = round(
            self.entries[url]['time_sum'] + request_time,
            self.ndigits
        )
        if Decimal(request_time) > Decimal(self.entries[url]['time_max']):
            self.entries[url]['time_max'] = request_time
        self.entries[url]['time_med'].add(request_time)

    def to_json(self, report_size):
        return json.dumps(
            sorted(
                self.entries.values(), key=lambda entry: - entry['time_sum']
            )[:report_size],
            default=lambda lazy_object: lazy_object()
        )

    @log_it(logging.INFO)
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
            logging.error('Directory {dir} is empty'.format(dir=logs_dir))
            return

    def get_report_name(self, log_path):
        re_time = re.compile(r'(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})')
        log_time = re_time.search(log_path).groupdict()
        return 'report-{Y}.{m}.{d}.html'.format(**log_time)

    def open_log(self, log_path):
        if log_path.endswith('gz'):
            log_file = gzip.open(log_path, 'rb', encoding='utf-8')
        else:
            log_file = open(log_path, 'r', encoding='utf-8')
        for line in log_file:
            yield line
        log_file.close()

    @log_it(logging.INFO)
    def create_report(self, logs_dir, report_dir, report_size):
        if os.path.exists(logs_dir):
            log_path = self.scan_dir(logs_dir)
            if log_path is None:
                logging.warning(
                    'File {} has been already handled.'.format(log_path)
                )
                return
        else:
            logging.error('Logs dir: {} is not found.'.format(logs_dir))
            return

        report_name = self.get_report_name(log_path)

        if not os.path.exists(os.path.join(report_dir, report_name)):
            for url, time in (self.parser.parse(line)
                              for line in self.open_log(log_path)):
                if url is not None:
                    self.report.add(url, time)
                else:
                    logging.warning('Can not handle url: {}.'.format(url))
                    continue
            report_path = os.path.join(report_dir, report_name)
            self.report.save(report_path, report_size)
            logging.info(
                'Log {} has been successfully created!'.format(report_name)
            )
            return report_path
        else:
            logging.error('Report {} already exists!'.format(report_name))


if __name__ == "__main__":

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt='[%(asctime)s] %(levelname).1s %(message)s',
            datefmt='%Y.%m.%d %H:%M:%S'
        )
    )
    logger.addHandler(handler)

    import time
    from datetime import datetime
    import argparse
    from configparser import RawConfigParser

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config', help='Path to the configuration file.',
        default='/usr/local/etc/log_nalyzer.conf'
    )
    args = parser.parse_args()
    config_path = args.config

    config_parser = RawConfigParser()
    config_parser.read(config_path)

    reports_size = int(config_parser.get('log_analyzer', 'report_size'))
    reports_dir = config_parser.get('log_analyzer', 'report_dir')
    logs_dir = config_parser.get('log_analyzer', 'log_dir')
    ts_file = config_parser.get('log_analyzer', 'ts_file')

    start_time = datetime.now()

    logs_analyzer = LogAnalyzer()
    report = logs_analyzer.create_report(logs_dir, reports_dir, reports_size)

    if report is not None:
        end_time = datetime.now()

        with open(ts_file, 'w', encoding='utf-8') as f:
            f.write(end_time.strftime('%Y.%m.%d %H:%M:%S'))

        os.utime(
            ts_file,
            (
                time.mktime(start_time.timetuple()),
                time.mktime(end_time.timetuple())
            )
        )

