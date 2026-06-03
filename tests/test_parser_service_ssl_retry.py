import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from requests.exceptions import HTTPError, SSLError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from services import parser_service
from utils import http_utils


SUBSCRIPTION_URL = "https://gQOW8QrZ.doggygo.top:8443/api/v1/client/82304bb2242720508e758014e28483a3"
CLASH_YAML = b"""
proxies:
  - name: test-node
    type: ss
    server: example.com
    port: 443
    cipher: aes-128-gcm
    password: secret
"""


class ProcessProxySourceSSLTests(unittest.TestCase):
    def test_preserve_host_case_helper_connects_with_original_netloc(self):
        connection = Mock()
        response = Mock(status=200, read=Mock(return_value=CLASH_YAML))
        connection.getresponse.return_value = response

        with patch("utils.http_utils.http.client.HTTPSConnection", return_value=connection) as https_connection:
            body = http_utils.http_get_preserve_host_case(SUBSCRIPTION_URL, timeout=5)

        self.assertEqual(CLASH_YAML, body)
        self.assertEqual("gQOW8QrZ.doggygo.top:8443", https_connection.call_args.args[0])
        self.assertEqual(5, https_connection.call_args.kwargs["timeout"])
        connection.request.assert_called_once_with(
            "GET",
            "/api/v1/client/82304bb2242720508e758014e28483a3",
            headers={
                "User-Agent": "FlClash/v0.8.90 clash-verge",
                "Host": "gQOW8QrZ.doggygo.top:8443",
            },
        )
        connection.close.assert_called_once()

    def test_retries_subscription_fetch_without_certificate_verification_after_ssl_error(self):
        req = Mock(url="http://111174.best/parse?name=xAFieLqrRt6orh69Ugh")
        req.headers = {}
        req.remote_addr = "218.249.167.22"
        source = {"name": "车神", "url": SUBSCRIPTION_URL}
        user_config = {"filter-proxy-name": [], "filter-proxy-server": []}

        with patch("utils.http_utils.requests.get") as requests_get:
            requests_get.side_effect = [
                SSLError("certificate verify failed: Hostname mismatch"),
                Mock(content=CLASH_YAML, raise_for_status=Mock()),
            ]

            proxies, group, names = parser_service.process_proxy_source(source, user_config, req)

        self.assertEqual(["test-node"], names)
        self.assertEqual("车神", group["name"])
        self.assertEqual("test-node", proxies[0]["name"])
        self.assertEqual(2, requests_get.call_count)
        self.assertEqual(True, requests_get.call_args_list[0].kwargs["verify"])
        self.assertEqual(False, requests_get.call_args_list[1].kwargs["verify"])
        self.assertEqual(5, requests_get.call_args_list[1].kwargs["timeout"])

    def test_does_not_disable_certificate_verification_for_non_ssl_errors(self):
        req = Mock(url="http://111174.best/parse?name=xAFieLqrRt6orh69Ugh")
        req.headers = {}
        req.remote_addr = "218.249.167.22"
        source = {"name": "车神", "url": SUBSCRIPTION_URL}
        user_config = {"filter-proxy-name": [], "filter-proxy-server": []}

        with patch("utils.http_utils.requests.get") as requests_get:
            response = Mock()
            response.raise_for_status.side_effect = HTTPError("404 Client Error")
            requests_get.return_value = response

            proxies, group, names = parser_service.process_proxy_source(source, user_config, req)

        self.assertIsNone(proxies)
        self.assertIsNone(group)
        self.assertIsNone(names)
        self.assertEqual(1, requests_get.call_count)
        self.assertEqual(True, requests_get.call_args.kwargs["verify"])

    def test_uses_case_preserved_https_fallback_when_unverified_retry_times_out(self):
        req = Mock(url="http://111174.best/parse?name=xAFieLqrRt6orh69Ugh")
        req.headers = {}
        req.remote_addr = "218.249.167.22"
        source = {"name": "车神", "url": SUBSCRIPTION_URL}
        user_config = {"filter-proxy-name": [], "filter-proxy-server": []}

        with patch("utils.http_utils.requests.get") as requests_get, patch("utils.http_utils.http_get_preserve_host_case") as preserve_case_get:
            requests_get.side_effect = [
                SSLError("certificate verify failed: Hostname mismatch"),
                TimeoutError("Read timed out"),
            ]
            preserve_case_get.return_value = CLASH_YAML

            proxies, group, names = parser_service.process_proxy_source(source, user_config, req)

        self.assertEqual(["test-node"], names)
        self.assertEqual("车神", group["name"])
        self.assertEqual("test-node", proxies[0]["name"])
        self.assertEqual(2, requests_get.call_count)
        self.assertEqual(False, requests_get.call_args_list[1].kwargs["verify"])
        self.assertEqual(5, requests_get.call_args_list[1].kwargs["timeout"])
        preserve_case_get.assert_called_once_with(SUBSCRIPTION_URL, timeout=5)

    def test_parse_route_outputs_subscription_after_ssl_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, "config")
            os.mkdir(config_dir)
            config_path = os.path.join(config_dir, "sslretry.yaml")
            with open(config_path, "w", encoding="utf-8") as config_file:
                config_file.write(
                    "pull-proxy-source:\n"
                    "  - name: 车神\n"
                    f"    url: \"{SUBSCRIPTION_URL}\"\n"
                )

            previous_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("utils.http_utils.requests.get") as requests_get:
                    requests_get.side_effect = [
                        SSLError("certificate verify failed: Hostname mismatch"),
                        Mock(content=CLASH_YAML, raise_for_status=Mock()),
                    ]

                    response = app.test_client().get("/parse?name=sslretry")
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(200, response.status_code)
        self.assertIn("test-node", response.get_data(as_text=True))
        self.assertIn("车神", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
