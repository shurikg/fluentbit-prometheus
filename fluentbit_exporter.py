from prometheus_client import Gauge, MetricsHandler
from prometheus_client.parser import text_string_to_metric_families

import json
import requests
import sys
from http.server import HTTPServer
import urllib.parse
import re

UNITS = {None: 1, "B": 1, "KB": 2 ** 10, "K": 2 ** 10, "MB": 2 ** 20, "M": 2 ** 20, "GB": 2 ** 30, "G": 2 ** 30, "TB": 2 ** 40}

def parse_size(size):
    if isinstance(size, int):
        return size
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGTB]?)?$', size.upper())
    if m:
        number, unit = m.groups()
        return int(float(number) * UNITS[unit])
    raise ValueError(f"Invalid human size [{size}]")

input_chunks_total = Gauge('input_chunks_total', 'input_chunks_total Number of chunks ', ['name'])
input_chunks_up = Gauge('input_chunks_up', 'input_chunks_up Number of up chunks ', ['name'])
input_chunks_down = Gauge('input_chunks_down', 'input_chunks_down Number of down chunks ', ['name'])
input_chunks_busy = Gauge('input_chunks_busy', 'input_chunks_busy Number of busy chunks ', ['name'])
input_chunks_busy_size_bytes = Gauge('input_chunks_busy_size_bytes', 'input_chunks_busy_size_bytes Number of busy chunks size bytes', ['name'])

input_chunks_status_overlimit = Gauge('input_chunks_status_overlimit', 'input_chunks_status_overlimit true or false', ['name'])
input_chunks_status_mem_size_bytes = Gauge('input_chunks_status_mem_size_bytes', 'input_chunks_status_mem_size_bytes Number of mem size in bytes', ['name'])
input_chunks_status_mem_limit_bytes = Gauge('input_chunks_status_mem_limit_bytes', 'input_chunks_status_mem_limit_bytes Number of mem limit in bytes', ['name'])

metrics = list()

PORT = ""

class MyRequestHandler(MetricsHandler):
    def do_GET(self):

        metrics.clear()

        for i in range(1, 3):
            metrics.append(
                Gauge(f'metric_{i}', f'metric_{i} Number of chunks ', ['name']))

        metrics[0].labels(name="aaa").set(10)
        metrics[1].labels(name="bbb").set(20)
        parsed_path = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        print(self.path, query)

        if("target" in query):
            host = query['target'][0]
            storageInfo = json.loads(requests.get(f'http://{host}/api/v1/storage').content.decode('UTF-8'))

            for current_input in storageInfo["input_chunks"]:
                input_chunks_total.labels(name=current_input).set(storageInfo["input_chunks"][current_input]['chunks']['total'])
                input_chunks_up.labels(name=[current_input]).set(int(storageInfo["input_chunks"][current_input]['chunks']['up']))
                input_chunks_down.labels(name=current_input).set(storageInfo["input_chunks"][current_input]['chunks']['down'])
                input_chunks_busy.labels(name=current_input).set(storageInfo["input_chunks"][current_input]['chunks']['busy'])
                input_chunks_busy_size_bytes.labels(name=current_input).set(parse_size(storageInfo["input_chunks"][current_input]['chunks']['busy_size']))

                input_chunks_status_overlimit.labels(name=current_input).set(storageInfo["input_chunks"][current_input]['status']['overlimit'])
                input_chunks_status_mem_size_bytes.labels(name=current_input).set(parse_size(storageInfo["input_chunks"][current_input]['status']['mem_size']))
                input_chunks_status_mem_limit_bytes.labels(name=current_input).set(parse_size(storageInfo["input_chunks"][current_input]['status']['mem_limit']))

            # metricsInfo = requests.get(
            #     f'{host}/api/v1/metrics/prometheus').content.decode('UTF-8')
            # print(text_string_to_metric_families(metricsInfo))

            # for family in text_string_to_metric_families(metricsInfo):
            #     for sample in family.samples:
            #         print(sample)
            #         print("Name: {0} Labels: {1} Value: {2}".format(*sample))
            return super(MyRequestHandler, self).do_GET()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"No target defined\n")


if __name__ == '__main__':
    PORT = sys.argv[1]

    server_address = ('', int(PORT))
    HTTPServer(server_address, MyRequestHandler).serve_forever()
