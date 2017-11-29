# The Nginx logs analyzer

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
