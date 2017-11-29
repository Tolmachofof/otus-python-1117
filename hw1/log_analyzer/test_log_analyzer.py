import unittest
from itertools import chain
from decimal import Decimal

from log_analyzer import Parser, UrlsReport, LogAnalyzer


class ParserTest(unittest.TestCase):

    def setUp(self):
        self.parser = Parser()

    def test_parse_url(self):
        correct_requests = (
            (
                'GET /api/v2/banner/25019354 HTTP/1.1',
                '/api/v2/banner/25019354'
            ),
            (
                'GET /api/v2/slot/4705/groups HTTP/1.1',
                '/api/v2/slot/4705/groups'
            ),
            (
                'GET /api/v2/banner/25013431 HTTP/1.1',
                '/api/v2/banner/25013431'
            )
        )
        incorrect_requests = (
            ('0', '0'),
            ('0', '0')
        )
        for request, result in chain(correct_requests, incorrect_requests):
            self.assertEqual(self.parser._parse_url(request), result)

    def test_parse_request_time(self):
        requests_time = (
            ('5.63', float('5.63')),
            ('1.0', float('1.0')),
            ('0', float('0'))
        )
        for time, result in requests_time:
            self.assertEqual(
                Decimal(self.parser._parse_request_time(time)),
                Decimal(result)
            )

    def test_parse(self):
        correct_logs = (
            (
                '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] '
                '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" '
                '"Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" '
                '"-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390',
                ('/api/v2/banner/25019354', float(0.390))
            ),
            (
                '1.168.65.96 -  - [29/Jun/2017:03:50:23 +0300] '
                '"GET /api/v2/internal/banner/24197629/info HTTP/1.1" 200 293 '
                '"-" "-" "-" "1498697423-2539198130-4708-9752783" '
                '"89f7f1be37d" 0.058',
                ('/api/v2/internal/banner/24197629/info', float(0.058))
            )
        )
        incorrect_logs = (
            ('-', (None, float(0))),
            ('- -  - - "-" - - "-" "-" "-" "-" "-" -', (None, float(0))),
            ('trash_string', (None, float(0)))
        )
        for log_string, result in chain(correct_logs, incorrect_logs):
            url, time = self.parser.parse(log_string)
            self.assertEqual(
                (url, Decimal(time)),
                (result[0], Decimal(result[1]))
            )
