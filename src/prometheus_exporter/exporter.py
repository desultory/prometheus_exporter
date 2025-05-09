"""
Basic exporter class for prometheus metrics.
The PrometheusRequest handler processes requests from Promotheus, by default returns server.export().
The server.export() method goes through all defined metrics and returns them as a string.
If a dict is passed to the export method, it will be used to filter by that label.
"""

from asyncio import all_tasks, ensure_future
from pathlib import Path
from signal import SIGHUP, SIGINT, signal
from tomllib import load

from aiohttp import web
from aiohttp.web import Application, Response, get
from zenlib.logging import ClassLogger

from .labels import Labels
from .metric import Metric

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 9999


class Exporter(ClassLogger):
    """
    Basic prometheus metric exporter class.
    Reads a config.toml file to read the server port and ip.

    When metrics are added from the config, they are added to self.metrics.
    Labels can be supplied as a dict as an argument, and in the config file.
    """

    def __init__(self, config_file="config.toml", name=None, labels=Labels(), no_config_file=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if name is not None:
            self.name = name
        self.labels = Labels(dict_items=labels, logger=self.logger)
        self.config_file = Path(config_file)
        if not no_config_file:
            signal(SIGHUP, lambda *args: self.read_config())
            self.read_config()
        else:
            self.config = {}
        self.listen_ip = kwargs.get("listen_ip", self.config.get("listen_ip", DEFAULT_IP))
        self.listen_port = kwargs.get("listen_port", self.config.get("listen_port", DEFAULT_PORT))

        self.app = Application(logger=self.logger)
        signal(SIGINT, lambda *args: ensure_future(self.app.shutdown()))
        self.app.on_startup.append(self.startup_tasks)
        self.app.add_routes([get("/metrics", self.handle_metrics)])
        self.app.on_shutdown.append(self.on_shutdown)

    @property
    def name(self):
        return getattr(self, "_name", self.__class__.__name__)

    @name.setter
    def name(self, value):
        if getattr(self, "_name", None) is not None:
            return self.logger.warning("[%s] Name already set, ignoring new name: %s", self.name, value)
        assert isinstance(value, str), "Name must be a string, not: %s" % type(value)
        self._name = value

    def __setattr__(self, name, value):
        if name == "labels":
            assert isinstance(value, Labels), "Labels must be a 'Labels' object."
        super().__setattr__(name, value)

    def read_config(self):
        """Reads the config file defined in self.config_file"""
        with open(self.config_file, "rb") as config:
            self.config = load(config)

        self.logger.info("Read config file: %s", self.config_file)
        self.labels |= self.config.get("labels", {})

    def start(self):
        """Starts the exporter server."""
        self.logger.info("Exporter server address: %s:%d" % (self.listen_ip, self.listen_port))
        web.run_app(self.app, host=self.listen_ip, port=self.listen_port)

    async def startup_tasks(self, *args, **kwargs):
        pass

    async def on_shutdown(self, app):
        self.logger.info("Shutting down exporter server")
        for task in all_tasks():
            if task.get_coro().__name__ in ["_run_app", "asyncTearDown"]:
                self.logger.debug("Skipping app task: %s", task)
                continue
            self.logger.info("Cancelling task: %s", task)
            task.cancel()

    def get_labels(self):
        """Returns a copy of the labels dict.
        This is designed to be extended, and the lables object may be modified by the caller.
        """
        return self.labels.copy()

    async def get_metrics(self, *args, **kwargs) -> list:
        """Returns a copy of the metrics list.
        This is designed to be extended in subclasses to get metrics from other sources.
        Clears the metric list before getting metrics, as layers may add metrics to the list.
        """
        self.metrics = []  # Clear the metrics list
        self.export_config_metrics()  # As an example, add metrics defined in the config
        return self.metrics.copy()  # Return a copy because the caller may modify the list for filtering

    def export_config_metrics(self, log_bump=10):
        """Adds all metrics defined in the config to self.metrics for exporting."""
        for name, values in self.config.get("metrics", {}).items():
            values = values.copy()
            kwargs = {
                "metric_type": values.get("type"),
                "labels": self.get_labels(),
                "logger": self.logger,
            }

            # Add labels specified under the metric to ones in the exporter
            if labels := values.pop("labels", None):
                kwargs["labels"].update(labels)

            self.logger.log(20 - log_bump, "Adding metric: %s", name)
            self.metrics.append(Metric(name=name, **kwargs, **values))

    async def handle_metrics(self, request, *args, **kwargs):
        params = dict([p.split("=") for p in request.query_string.split("&")]) if request.query_string else {}
        self.logger.debug("[%s] Handling metrics request: %s" % (request.remote, request.query_string))
        response = Response(text=await self.export(params))
        self.logger.info(
            "[%s (%s)] Sending response: <%d> Length: %d"
            % (request.remote, request.query_string, response.status, response.content_length)
        )
        return response

    async def export(self, label_filter=None):
        """Gets metrics using self.metrics Turns them into a metric string for prometheus."""
        label_filter = label_filter or {}
        output = ""
        for metric in await self.get_metrics(label_filter=label_filter):
            self.logger.log(5, "Checking metric: %s", metric)
            if metric.check_labels(label_filter) and metric.value is not None:
                output += f"{metric}\n"

        self.logger.debug("Exporting metrics:\n%s", output)
        return output

    def __str__(self):
        metric_data = "\n".join([str(metric) for metric in self.metrics])
        return f"<Exporter host={self.listen_ip}:{self.listen_port} metrics={len(self.metrics)}>\n{metric_data}"
