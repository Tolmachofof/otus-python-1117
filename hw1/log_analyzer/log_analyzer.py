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
from collections import defaultdict
from functools import wraps


DEFAULT_CONF = {
    'report_size': 1000,
    'report_dir': './',
    'log_dir': './',
    'ts_file': './log_analyzer.ts',
}


DT_PATTERN = re.compile(r'(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})')
LOG_PATTERN = re.compile(
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
FIELDS = ('request', 'request_time', )
PARSERS = {'request': lambda r: r.split(' ')[1]}


def log_it(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            logging.info("Started: {}.".format(fn.__name__))
            result = fn(*args, **kwargs)
            logging.info("Finished: {}.".format(fn.__name__))
            return result
        except Exception as exc:
            logging.exception("Error in {}".format(fn.__name__))
            raise exc
    return wrapper


def parse(entry, pattern=LOG_PATTERN, fields=FIELDS,
          parsers=PARSERS):
    parsed_entry = pattern.match(entry)

    if parsed_entry is not None:
        parsed_entry = parsed_entry.groupdict()
        for field, parser in parsers.items():
            try:
                parsed_entry[field] = parser(parsed_entry.get(field))
            except Exception:
                parsed_entry[field] = None
        return {field: parsed_entry.get(field) for field in fields}


@log_it
def scan_dir(dir_path, file_name_pattern, dt_pattern=DT_PATTERN):
    log_files = glob.glob(os.path.join(dir_path, file_name_pattern))
    try:
        return max(log_files, key=lambda file: dt_pattern.match(file))
    except ValueError:
        return


def read_file(path):
    if path.endswith('gz'):
        log_file = gzip.open(path, 'rb', encoding='utf-8')
    else:
        log_file = open(path, 'r', encoding='utf-8')
    for line in log_file:
        yield line
    log_file.close()


def get_perc(value, total, ndigits=2):
    return round(value / (total / 100), ndigits)


def get_mid(value, total, ndigits=2):
    return round(total / value, ndigits)


@log_it
def create_report(log_path, r_size=1000):
    r_total = 0
    t_all = 0
    report = defaultdict(lambda: defaultdict(lambda: 0))
    for entry in (parse(line) for line in read_file(log_path)):
        if entry is None:
            continue

        url = entry.get('request') or '-'
        r_time = float(entry.get('request_time')) or float(0)
        if url not in report:
            report[url]['count_perc'] = lambda: get_perc(
                report[url]['count'], r_total
            ),
            report[url]['time_perc'] = lambda: get_perc(
                report[url]['time_sum'], t_all
            ),
            report[url]['time_avg'] = lambda: get_perc(
                report[url]['time_sum'], report[url]['count']
            )
        report[url]['count'] += 1
        report[url]['time_sum'] = round(report[url]['time_sum'] + r_time, 2)
        if r_time > report[url]['time_max']:
            report[url]['time_max'] = r_time

        r_total += 1
        t_all = round(t_all + r_time, 2)

    result = sorted(report.values(), key=lambda entry: - entry['time_sum'])[:r_size]
    return json.dumps(result, default=lambda lazy_obj: lazy_obj())


@log_it
def save_report(report, report_path):
    with open('./templates/report.html', 'r', encoding='utf-8') as f:
        template = f.read()

    template = template.replace('$table_json', report)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(template)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config', help='Path to the configuration file.',
        default='/usr/local/etc/log_analyzer.conf'
    )
    args = parser.parse_args()
    config_path = args.config
    if config_path is not None:
        config_parser = RawConfigParser()
        config_parser.read(config_path)
        config = config_parser._sections.get('log_analyzer', {})
    else:
        config = DEFAULT_CONF
    for item in set(DEFAULT_CONF.keys()).difference(set(config.keys())):
        config[item] = DEFAULT_CONF[item]
    return config


@log_it
def main(logs_dir, reports_dir, report_size):
    log_template = 'nginx-access-ui*'
    report_template = 'report-{Y}.{m}.{d}.html'

    if not os.path.exists(logs_dir) or not os.path.exists(reports_dir):
        logging.error('Wrong logs/reports path!')
        return

    log_path = scan_dir(logs_dir, log_template)
    if log_path is None:
        logging.error('Logs dir {} is empty!'.format(logs_dir))
        return

    report_name = report_template.format(
        **DT_PATTERN.search(log_path).groupdict()
    )
    report_path = os.path.join(reports_dir, report_name)
    if not os.path.exists(report_path):
        report = create_report(log_path)
        save_report(report, report_path)
    else:
        logging.error('Log {} has already been handled!'.format(log_path))


if __name__ == "__main__":

    import time
    from datetime import datetime
    import argparse
    from configparser import RawConfigParser

    config = parse_args()
    log_file = config.get('log_file')
    if log_file is not None:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler()
    logging.basicConfig(
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        handlers=[handler]
    )

    start_time = datetime.now()
    main(config['log_dir'], config['report_dir'], config['report_size'])
    end_time = datetime.now()

    os.utime(
        config['ts_file'],
        (
            time.mktime(start_time.timetuple()),
            time.mktime(end_time.timetuple())
        )
    )

