"""
Basic exporter class for prometheus metrics.
Runs a ThreadingHTTPServer with a PrometheusRequest handler.
The PrometheusRequest handler processes requests from Promotheus, by default returns server.export().
The server.export() method goes through all defined metrics and returns them as a string.
If a dict is passed to the export method, it will be used to filter by that label.
"""

from http.server import ThreadingHTTPServer
from pathlib import Path

from zenlib.logging import loggify

from .labels import Labels
from .metric import Metric
from .prometheus_request import PrometheusRequest

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 9999


@loggify
class Exporter(ThreadingHTTPServer):
    """
    Basic prometheus metric exporter class.
    Extends the ThreadingHTTPServer class.
    Forces use of the PrometheusRequest RequestHandlerClass.
    Reads a config.toml file to read the server port and ip.
    If 'ip' and 'port' are passed as kwargs, they will override the config file.

    When metrics are added from the config, they are added to self.metrics.
    Labels can be supplied as a dict as an argument, and in the config file.
    """
    def __init__(self, config_file='config.toml', labels=Labels(), *args, **kwargs):
        self.labels = Labels(dict_items=labels, logger=self.logger, _log_init=False)
        self.metrics = []
        self.config_file = Path(config_file)
        self.read_config()

        kwargs['RequestHandlerClass'] = PrometheusRequest
        ip = kwargs.pop('ip') if 'ip' in kwargs else self.config.get('listen_ip', DEFAULT_IP)
        port = kwargs.pop('port') if 'port' in kwargs else self.config.get('listen_port', DEFAULT_PORT)
        kwargs['server_address'] = (ip, port)

        self.logger.info("Exporter server address: %s:%d" % (*kwargs['server_address'], ))

        super().__init__(*args, **kwargs)

    def __setattr__(self, name, value):
        if name == 'labels' and not isinstance(value, Labels):
            raise ValueError("Labels must be a dict.")
        super().__setattr__(name, value)

    def read_config(self):
        """ Reads the config file defined in self.config_file """
        from tomllib import load
        with open(self.config_file, 'rb') as config:
            self.config = load(config)

        self.logger.info("Read config file: %s", self.config_file)
        self.labels.update(self.config.get('labels', {}))

        self.add_config_metrics()

    def add_config_metrics(self):
        """ Adds all metrics defined in the config to the exporter. """
        for name, values in self.config.get('metrics', {}).items():
            kwargs = {'metric_type': values.pop('type'), 'labels': self.labels.copy(),
                      'logger': self.logger, '_log_init': False}

            # Add labels specified under the metric to ones in the exporter
            if labels := values.pop('labels', None):
                kwargs['labels'].update(labels)

            self.logger.info("Adding metric: %s", name)
            self.metrics.append(Metric(name=name, **kwargs, **values))

    def filter_metrics(self, label_filter={}):
        """ Filters metrics by label. """
        return self.get_labels().filter_metrics(self._get_metrics(), label_filter)

    def get_labels(self):
        """ Gets a copy of the labels dict. """
        return self.labels.copy()

    def _get_metrics(self):
        """ Gets all defined metrics. """
        return self.metrics

    def get_metrics(self, label_filter={}):
        """ Gets all defined metrics, filtered by label_filter Can be overridden to use other methods."""
        return self.filter_metrics(label_filter)

    def export(self, label_filter={}):
        """
        Gets metrics using self.get_metrics(), passing the label_filter.
        Turns them into a metric string for prometheus.
        """
        metrics = self.get_metrics(label_filter)
        self.logger.debug("Exporting metrics: %s", metrics)
        return "\n".join([str(metric) for metric in metrics])

    def handle_error(self, request, client_address):
        """ Handle errors in the request handler. """
        from sys import exc_info
        from traceback import format_exception
        self.logger.warning("[%s:%d] Error in request: %s" % (*client_address, exc_info()[1]))
        exc = format_exception(*exc_info())
        self.logger.debug(''.join(exc).replace(r'\n', '\n'))
