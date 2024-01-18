from enum import Enum

from zenlib.logging import loggify

from .labels import Labels


class MetricTypes(Enum):
    """
    Prometheus metric types
    """
    COUNTER = 'counter'
    GAUGE = 'gauge'
    UNTYPED = 'untyped'


@loggify
class Metric:
    """
    Represents a Prometheus metric.
    Labels can be added to the metric by passing a dictionary as the labels argument.
    The value defaults to 0.
    The metric type defaults to 'untyped'.
    """
    def __init__(self, name, value=0, metric_type='untyped', help=None, labels=Labels(), *args, **kwargs):
        self.name = name
        self.type = metric_type
        self.help = help
        self.labels = Labels(labels, logger=self.logger, _log_init=False)
        self.value = value

    def check_labels(self, label_filter):
        """
        Check if the metric labels match the label filter.
        label_filter can be a dictionary or a Labels object.
        """
        self.logger.log(5, 'Checking labels: %s' % label_filter)
        for label, value in label_filter.items():
            if label not in self.labels or self.labels[label] != value:
                return False
        return True

    def __setattr__(self, name, value):
        """
        Ensure name is not changed after creation.
        Turn spaces in the name into underscores.
        Set the metric type based on the MetricTypes enum.
        """
        if name == 'name':
            if hasattr(self, 'name'):
                raise AttributeError('Cannot change metric name')
            value = value.replace(' ', '_')
        elif name == 'type':
            value = MetricTypes[value.upper()]
        elif name == 'value':
            if not isinstance(value, (int, float)):
                raise TypeError('Value must be an integer or float')
        super().__setattr__(name, value)

    def __getattribute__(self, name):
        """ Return the result of value() if the method exists, otherwise return the attribute """
        if name == 'value' and hasattr(self, '_value'):
            return self._value()
        return super().__getattribute__(name)

    def __str__(self):
        """ Get a string representation of the metric for Prometheus """
        # Start by adding the help text if it exists
        if self.help:
            out_str = f'# HELP {self.name} {self.help}\n'
        else:
            out_str = ''

        out_str += f'# TYPE {self.name} {self.type.value}\n{self.name}'

        # Add labels if they exist
        if self.labels:
            out_str = f"{out_str}{{{self.labels}}}"

        out_str += f' {self.value}'
        return out_str
