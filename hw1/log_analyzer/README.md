# The Nginx logs analyzer
Парсер логов nginx.
По итогам своей работы создает отчет report-{datetime}.html, 
который содержит сводную статистику для каждого URL из лога:
```
count - сколько раз встречается URL, абсолютное значение
count_perc - сколько раз встречается URL, в процентнах относительно общего числа запросов
time_sum - суммарный $request_time для данного URL'а, абсолютное значение
time_perc - суммарный $request_time для данного URL'а, в процентах относительно общего $request_time всех запросов
time_avg - средний $request_time для данного URL'а
time_max - максимальный $request_time для данного URL'а
time_med - медиана $request_time для данного URL'а
```
## Python requirements
Python 3.5 or later.

### Nginx logs format:
```
'$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" $status $body_bytes_sent "$http_referer" ' '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" $request_time'
```
### Log example:
```
1.168.65.96 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/test HTTP/1.1" 200 293 "-" "-" "-" "1498697423-2539198130-4708-9752783" "89f7f1be37d" 0.058
```
### Run example:
```
python log_analyzer --config=log_analyzer.conf
```
### Running the tests
```
python -m unittest test_log_analyzer
```
При отсутствии параметра --config при вызове скрипта используется conf файл из директории: 
/usr/local/etc/log_analyzer.conf
### Config format:
```
REPORT_SIZE = 1000 - Количество уникальных URL'ов, которые попадут в отчет.
REPORT_DIR =./reports - Папка с шаблоном отчета.
LOG_DIR = ./log - Папка с логами nginx.
TS_FILE = ./log_analyzer.ts - TS файл с датой последнего запуска скрипта.
LOG_FILE = ./log_analyzer.log - Опциональный параметр. Если указан, скрипт пишет логи в заданный файл.
```
