import os
import unittest
import urllib.error
import urllib.request

BASE_URL = os.getenv("SHOPSPHERE_TEST_URL", "http://127.0.0.1:18000")


def get_json(path):
    request = urllib.request.Request(
        BASE_URL + path,
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read().decode("utf-8")


class ShopSphereAPITests(unittest.TestCase):
    def test_home(self):
        status, body = get_json("/")
        self.assertEqual(status, 200)
        self.assertIn("ShopSphere", body)

    def test_health(self):
        status, body = get_json("/health")
        self.assertEqual(status, 200)
        self.assertIn('"healthy"', body)

    def test_ready(self):
        status, body = get_json("/ready")
        self.assertEqual(status, 200)
        self.assertIn('"ready"', body)

    def test_version(self):
        status, body = get_json("/version")
        self.assertEqual(status, 200)
        self.assertIn("version", body)

    def test_metrics(self):
        request = urllib.request.Request(BASE_URL + "/metrics")
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8")
        self.assertIn("shopsphere_api_http_requests_total", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
