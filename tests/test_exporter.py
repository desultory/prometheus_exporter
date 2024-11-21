from asyncio import run
from unittest import TestCase, expectedFailure, main
from uuid import uuid4

from aiohttp.test_utils import AioHTTPTestCase
from prometheus_exporter import Exporter
from zenlib.logging import loggify


def generate_random_metric_config(count: int) -> dict:
    """Generate a random metric configuration"""
    metrics = {}
    for i in range(count):
        name = "x" + str(uuid4()).replace("-", "_")
        metrics[name] = {"type": "counter", "help": str(uuid4())}
    return metrics


class TestExporter(TestCase):
    @expectedFailure
    def test_no_config(self):
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
