from unittest import TestCase, expectedFailure, main

from prometheus_exporter import Labels, Metric
from prometheus_exporter.metric import MetricTypes
from zenlib.logging import loggify


class ExampleMetric(Metric):
    def _value(self):
        return 42


class ExampleCounterMetric(Metric):
    def __init__(self, name, **kwargs):
        kwargs.pop("metric_type", None)
        kwargs.pop("type", None)
        self.count = 0
        super().__init__(name, metric_type=MetricTypes.COUNTER, **kwargs)

    def _value(self):
        self.count += 1
        return self.count


@loggify
class TestMetrics(TestCase):
    def test_simple_metric(self):
        metric = Metric("test")
        self.assertEqual(metric.name, "test")
        self.assertEqual(metric.labels, Labels())
        self.assertEqual(metric.value, 0)
        self.assertEqual(metric.type, MetricTypes.UNTYPED)
        self.assertEqual(metric.help, None)
        metric_string = "# TYPE test untyped\ntest 0"
        self.assertEqual(str(metric), metric_string)

    def test_metric_with_labels(self):
        test_labels = Labels({"label1": "value1"})
        metric = Metric("test", labels=test_labels)
        self.assertEqual(metric.labels, test_labels)
        metric_string = '# TYPE test untyped\ntest{label1="value1"} 0'
        self.assertEqual(str(metric), metric_string)

    def test_metric_with_help(self):
        metric = Metric("test", help="This is a test metric")
        self.assertEqual(metric.help, "This is a test metric")
        metric_string = "# HELP test This is a test metric\n# TYPE test untyped\ntest 0"
        self.assertEqual(str(metric), metric_string)

    def test_metric_with_help_and_labels(self):
        test_labels = Labels({"label1": "value1"})
        metric = Metric("test", help="This is a test metric", labels=test_labels)
        self.assertEqual(metric.help, "This is a test metric")
        self.assertEqual(metric.labels, test_labels)
        metric_string = '# HELP test This is a test metric\n# TYPE test untyped\ntest{label1="value1"} 0'
        self.assertEqual(str(metric), metric_string)

    def test_example_metric(self):
        metric = ExampleMetric("test")
        self.assertEqual(metric.name, "test")
        self.assertEqual(metric.value, 42)
        metric_string = "# TYPE test untyped\ntest 42"
        self.assertEqual(str(metric), metric_string)

    def test_example_counter_metric(self):
        metric = ExampleCounterMetric("test")
        self.assertEqual(metric.name, "test")
        self.assertEqual(metric.value, 1)
        metric_string = "# TYPE test counter\ntest 2"  # it should increment
        self.assertEqual(str(metric), metric_string)

    @expectedFailure
    def test_bad_name(self):
        Metric("123test")

    def test_space_to_underscore(self):
        metric = Metric("test metric")
        self.assertEqual(metric.name, "test_metric")

    def test_counter_type(self):
        metric = Metric("test", metric_type="counter")
        self.assertEqual(metric.type, MetricTypes.COUNTER)
        metric_string = "# TYPE test counter\ntest 0"
        self.assertEqual(str(metric), metric_string)

    def test_gauge_type(self):
        metric = Metric("test", metric_type="gauge")
        self.assertEqual(metric.type, MetricTypes.GAUGE)
        metric_string = "# TYPE test gauge\ntest 0"
        self.assertEqual(str(metric), metric_string)

    def test_type_from_enum(self):
        metric = Metric("test", metric_type=MetricTypes.COUNTER)
        self.assertEqual(metric.type, MetricTypes.COUNTER)
        metric_string = "# TYPE test counter\ntest 0"
        self.assertEqual(str(metric), metric_string)

    def test_type_from_type(self):
        """Use 'type' instead of 'metric_type'"""
        metric = Metric("test", type=MetricTypes.GAUGE)
        self.assertEqual(metric.type, MetricTypes.GAUGE)
        metric_string = "# TYPE test gauge\ntest 0"
        self.assertEqual(str(metric), metric_string)


if __name__ == "__main__":
    main()
