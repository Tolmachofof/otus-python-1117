import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory, TemporaryFile

from log_analyzer import parse, scan_dir


class TestLogAnalyzer(unittest.TestCase):

    def test_parse(self):
        logs = (
            (
                '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] '
                '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" '
                '"Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" '
                '"-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390',
                {
                    'request': '/api/v2/banner/25019354',
                    'request_time': '0.390'
                }
            ),
            (
                '1.168.65.96 -  - [29/Jun/2017:03:50:23 +0300] '
                '"GET /api/v2/internal/banner/24197629/info HTTP/1.1" 200 293 '
                '"-" "-" "-" "1498697423-2539198130-4708-9752783" '
                '"89f7f1be37d" 0.058',
                {
                    'request': '/api/v2/internal/banner/24197629/info',
                    'request_time': '0.058'
                }
            )
        )
        for log_string, result in logs:
            p_result = parse(log_string)
            self.assertEqual(result['request'], p_result['request'])
            self.assertAlmostEqual(
                float(result['request_time']),
                float(p_result['request_time'])
            )
            
    def test_scan_dir(self):
        file_names = [
            'nginx-access-ui.log-20170630', 'nginx-access-ui.log-20170631',
            'nginx-access-ui.log-20170632', 'nginx-access-ui.log-20170633',
        ]
        with patch('glob.glob', lambda dir_path: file_names):
            self.assertEqual(
                scan_dir('./', 'nginx-access-ui*'),
                'nginx-access-ui.log-20170633'
            )


        