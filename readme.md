# Prometheus Exporter

A simple prometheus exporter library using:

* [aiohttp](https://github.com/aio-libs/aiohttp)
* [zenlib](https://github.com/desultory/zenlib)

## Features

* async via aiohttp
* detailed logging
* toml config
* optional caching

## Components

### Labels

The `Labels` dict represents a collection of labels and ensures added labels are strings.

The `__str__` method is overridden so that when printed, the object returns a formatted label string for exporting.

`copy()` ensures the copy is also a Labels type, and has a logger from the same parent.

### Metric

The `Metric` class represents a prometheus metric.

It must be defined with a name, and defaults to the value `0`.

Optionally the following parameters can be passed:

* `metric_type` (`untyped`) Prometheus metric type
* `help` (`None`) The metric help string
* `labels` (`Labels()`) Label dictionary for the metric.

`check_filter(label_filter)` can be used to pass a label filter to the metric, returning `True` if the labels match.

`__str__` is overridden to print out a proper metric string based on the contents of the object.

### Exporter

The `Exporter` is responsible for collecting and exporting metrics.

The following arguments can be used:

* `config_file` (`config.toml`) The config file for the exporter.
* `labels` (`Labels()`) Label dictionary for the exporter, passed to created metrics.
* `listen_ip` (`127.0.0.1`) The IP address to run the exporter on.
* `listen_port` (`9999`) The port to listen on.

Once created the exporter can be started with: `start()`

Requests to `/metrics` are handled by `handle_metrics(request)`.


