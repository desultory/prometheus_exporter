from unittest import TestCase, expectedFailure, main
from uuid import uuid4

from aiohttp.test_utils import AioHTTPTestCase
from prometheus_exporter import Exporter
from zenlib.logging import loggify


class TestExporter(TestCase):
    @expectedFailure
    def test_no_config(self):
        Exporter(config_file=str(uuid4()))  # Pass a random string as config

    def test_proper_no_config(self):
        """Test init with no_config_file set to True"""
        Exporter(no_config_file=True)


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
        """Test the exporter server by sending a request to the /metrics endpoint"""
        expected_response = await self.exporter.export(label_filter={"label1": "value1"})
        async with self.client.get("/metrics?label1=value1") as response:
            self.assertEqual(response.status, 200)
            text = await response.text()
            self.assertEqual(text, expected_response)


if __name__ == "__main__":
    main()
