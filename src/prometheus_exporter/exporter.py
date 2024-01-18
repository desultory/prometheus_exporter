"""
Basic exporter class for prometheus metrics.
The PrometheusRequest handler processes requests from Promotheus, by default returns server.export().
The server.export() method goes through all defined metrics and returns them as a string.
If a dict is passed to the export method, it will be used to filter by that label.
"""

from aiohttp.web import Application, Response, get
from pathlib import Path
from signal import signal, SIGHUP

from zenlib.logging import ClassLogger

from .labels import Labels
from .metric import Metric

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 9999


class Exporter(ClassLogger):
    """
    Basic prometheus metric exporter class.
    Reads a config.toml file to read the server port and ip.

    When metrics are added from the config, they are added to self.metrics.
    Labels can be supplied as a dict as an argument, and in the config file.
    """
    def __init__(self, config_file='config.toml', labels=Labels(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.labels = Labels(dict_items=labels, logger=self.logger, _log_init=False)
        self.config_file = Path(config_file)
        signal(SIGHUP, lambda *args: self.read_config())
        self.read_config()
        self.host = kwargs.get('host', self.config.get('listen_ip', DEFAULT_IP))
        self.port = kwargs.get('port', self.config.get('listen_port', DEFAULT_PORT))

        self.app = Application(logger=self.logger)
        self.app.add_routes([get('/metrics', self.handle_metrics)])

    def __setattr__(self, name, value):
        if name == 'labels':
            assert isinstance(value, Labels), "Labels must be a 'Labels' object."
        super().__setattr__(name, value)

    def get_labels(self):
        return self.labels.copy()

    async def get_metrics(self, *args, **kwargs):
        self.metrics = []
        self.add_config_metrics(log_bump=10)
        return self.metrics.copy()

    def read_config(self):
        """ Reads the config file defined in self.config_file """
        from tomllib import load
        with open(self.config_file, 'rb') as config:
            self.config = load(config)

        self.logger.info("Read config file: %s", self.config_file)
        self.labels |= self.config.get('labels', {})

    def start(self):
        """ Starts the exporter server. """
        from aiohttp import web
        self.logger.info("Exporter server address: %s:%d" % (self.host, self.port))
        web.run_app(self.app, host=self.host, port=self.port)

    async def handle_metrics(self, request, *args, **kwargs):
        params = dict([p.split('=') for p in request.query_string.split('&')]) if request.query_string else {}
        self.logger.debug("[%s] Handling metrics request: %s" % (request.remote, request.query_string))
        response = Response(text=await self.export(params))
        self.logger.info("[%s (%s)] Sending response: <%d> Length: %d" % (request.remote, request.query_string, response.status, response.content_length))
        return response

    def add_config_metrics(self, log_bump=0):
        """ Adds all metrics defined in the config to the exporter. """
        for name, values in self.config.get('metrics', {}).items():
            kwargs = {'metric_type': values.pop('type'), 'labels': self.get_labels(),
                      'logger': self.logger, '_log_init': False}

            # Add labels specified under the metric to ones in the exporter
            if labels := values.pop('labels', None):
                kwargs['labels'].update(labels)

            self.logger.log(20 - log_bump, "Adding metric: %s", name)
            self.metrics.append(Metric(name=name, **kwargs, **values))

    async def export(self, label_filter={}):
        """ Gets metrics using self.metrics Turns them into a metric string for prometheus. """
        output = ""
        for metric in await self.get_metrics(label_filter=label_filter):
            self.logger.log(5, "Checking metric: %s", metric)
            if metric.check_labels(label_filter):
                output += f'{metric}\n'

        self.logger.debug("Exporting metrics:\n%s", output)
        return output

    def __str__(self):
        metric_data = '\n'.join([str(metric) for metric in self.metrics])
        return f"<Exporter host={self.host} port={self.port} metrics={len(self.metrics)}>\n{metric_data}"
