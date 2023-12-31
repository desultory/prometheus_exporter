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

    def get_metrics(self):
        """ Gets all defined metrics. """
        return [metric for metric in self.metrics]

    def _filter_metrics(self, metrics, label_filter):
        """ Filters a list of metrics by a label_filter. """
        filtered_metrics = []
        for label_name, label_value in label_filter.items():
            if label_name not in self.labels.global_labels:
                raise ValueError("Unknown label: %s" % label_name)
            if label_value not in self.labels.global_labels[label_name]:
                raise ValueError("[%s] Unknown label value: %s" % (label_name, label_value))

            # If metrics have already been filtered, filter them again so labels act as an "and" filter.
            if filtered_metrics:
                metrics = filtered_metrics
                filtered_metrics = []

            for metric in metrics:
                if label_name in metric.labels and metric.labels[label_name] == label_value:
                    filtered_metrics.append(metric)

        return filtered_metrics

    def export(self, label_filter=None):
        """
        Go through metrics in self.metrics, turn them into a metric string for prometheus.
        If a label_filter is passed, only return metrics that match the label_filter.
        """
        metrics = self.get_metrics()
        if label_filter:
            metrics = self._filter_metrics(metrics, label_filter)
        return "\n".join([str(metric) for metric in metrics])

    def handle_error(self, request, client_address):
        """ Handle errors in the request handler. """
        from sys import exc_info
        from traceback import format_exception
        self.logger.warning("[%s:%d] Error in request: %s" % (*client_address, exc_info()[1]))
        exc = format_exception(*exc_info())
        self.logger.debug(''.join(exc).replace(r'\n', '\n'))
