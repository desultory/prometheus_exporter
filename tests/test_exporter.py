from asyncio import run
from unittest import TestCase, main
from uuid import uuid4

from aiohttp.test_utils import AioHTTPTestCase
from prometheus_exporter import Exporter, cached_exporter
from zenlib.logging import loggify

@cached_exporter
class TestCachedExporter(Exporter):
    async def get_metrics(self, *args, **kwargs) -> dict:
        metrics = await super().get_metrics(*args, **kwargs)
        print("Getting metrics:", metrics)
        return metrics

def generate_random_metric_config(count: int) -> dict:
    """Generate a random metric configuration"""
    metrics = {}
    for i in range(count):
        name = "x" + str(uuid4()).replace("-", "_")
        metrics[name] = {"type": "counter", "help": str(uuid4())}
    return metrics


class TestExporter(TestCase):
    def test_no_config(self):
        with self.assertRaises(FileNotFoundError):
            Exporter(config_file=str(uuid4()))  # Pass a random string as config

    def test_proper_no_config(self):
        e = Exporter(no_config_file=True)
        self.assertIsNotNone(run(e.export()))

    def test_random_metrics(self):
        """Ensure metrics are the same run to run and properly export 100 random metrics"""
        e = Exporter(no_config_file=True)
        random_metrics = generate_random_metric_config(100)
        e.config["metrics"] = random_metrics
        export1 = run(e.export())
        export2 = run(e.export())
        self.assertEqual(export1, export2)
        for metric in random_metrics:
            self.assertIn(f"{metric} 0", export1)

    def test_cached_exporter(self):
        e = TestCachedExporter(no_config_file=True)
        e.config["metrics"] = generate_random_metric_config(100)
        export1 = run(e.export())
        e.config["metrics"] = generate_random_metric_config(100)
        export2 = run(e.export())
        self.assertEqual(export1, export2)
        e.cache_time = 0
        export3 = run(e.export())
        self.assertNotEqual(export1, export3)

    def test_global_labels(self):
        """Ensures that lables which are defined globally are applied to all metrics"""
        e = Exporter(labels={"global_label": "global_value"}, no_config_file=True)
        random_metrics = generate_random_metric_config(10)
        e.config["metrics"] = random_metrics
        export = run(e.export())
        for metric in random_metrics:
            self.assertIn(f'{metric}{{global_label="global_value"}} 0', export)

    def test_global_labels_override(self):
        """Ensures that global labels defined in a metric's config override the global labels"""
        e = Exporter(labels={"global_label": "global_value"}, no_config_file=True)
        random_metrics = generate_random_metric_config(10)
        e.config["metrics"] = {
            **random_metrics,
            "test_metric": {"type": "counter", "help": "test", "labels": {"global_label": "local_value"}},
        }
        export = run(e.export())
        self.assertIn('test_metric{global_label="local_value"} 0', export)
        for metric in random_metrics:
            self.assertIn(f'{metric}{{global_label="global_value"}} 0', export)

    def test_edited_metric_labels(self):
        """Test that editing labels on an added metric do not affect global labels"""
        test_labels = {"label1": "value1", "label2": "value2"}
        e = Exporter(no_config_file=True, labels=test_labels)
        random_metrics = generate_random_metric_config(10)
        e.config["metrics"] = random_metrics
        e.metrics = []
        e.export_config_metrics()  # Generate metrics from the config
        for metric in e.metrics:
            self.assertEqual(metric.labels, test_labels)
            metric.labels = {"asdf": str(uuid4())}
        self.assertEqual(e.labels, test_labels)

    def test_append_metrics(self):
        """Ensures metrics can be appended after init"""
        e = Exporter(no_config_file=True)
        random_metrics_a = generate_random_metric_config(10)
        random_metrics_b = generate_random_metric_config(10)
        all_metrics = {**random_metrics_a, **random_metrics_b}
        e.config["metrics"] = random_metrics_a
        export1 = run(e.export())
        e.config["metrics"].update(random_metrics_b)
        export2 = run(e.export())
        self.assertNotEqual(export1, export2)
        for metric in all_metrics:
            self.assertIn(f"{metric} 0", export2)

    def test_metric_filter(self):
        """Ensure metrics can be filtered by label"""
        e = Exporter(config_file="tests/test_config.toml")
        label_filter = {"label1": "value1"}
        export = run(e.export(label_filter=label_filter))
        self.assertEqual(
            export,
            '# TYPE test_metric_with_labels untyped\ntest_metric_with_labels{label1="value1",label2="value2"} 300\n',
        )


@loggify
class TestExporterAsync(AioHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.exporter = Exporter(config_file="tests/test_config.toml", logger=self.logger)

    async def get_application(self):
        return self.exporter.app

    async def test_exporter(self):
        """Test the exporter server by sending a request to the /metrics endpoint"""
        expected_response = await self.exporter.export()
        async with self.client.get("/metrics") as response:
            self.assertEqual(response.status, 200)
            text = await response.text()
            self.assertEqual(text, expected_response)

    async def test_filter(self):
        """Test the exporter webserver filter by sending a request with args to the /metrics endpoint"""
        expected_response = await self.exporter.export(label_filter={"label1": "value1"})
        async with self.client.get("/metrics?label1=value1") as response:
            self.assertEqual(response.status, 200)
            text = await response.text()
            self.assertEqual(text, expected_response)

    async def test_random_metrics(self):
        """Ensure the server can properly serve 1000 random metrics"""
        random_metrics = generate_random_metric_config(1000)
        self.exporter.config["metrics"] = random_metrics
        expected_response = await self.exporter.export()
        async with self.client.get("/metrics") as response:
            self.assertEqual(response.status, 200)
            text = await response.text()
            self.assertEqual(text, expected_response)
        for metric in random_metrics:
            self.assertIn(f"{metric} 0", text)


if __name__ == "__main__":
    main()
