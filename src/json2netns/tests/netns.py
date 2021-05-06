#!/usr/bin/env python3

import unittest
from ipaddress import IPv4Interface, IPv6Interface
from pathlib import Path
from unittest.mock import patch


from json2netns.netns import Namespace, load_config

BASE_PATH = Path(__file__).parent.parent.resolve()
BASE_MODULE = "json2netns.netns"
SAMPLE_JSON_CONF_PATH = BASE_PATH / "sample.json"


class NetNSTests(unittest.TestCase):
    def setUp(self) -> None:
        config = load_config(SAMPLE_JSON_CONF_PATH)
        for ns_name, ns_conf in config["namespaces"].items():
            self.test_ns = Namespace(ns_name, ns_conf, config)
            break

    def test_check(self) -> None:
        with patch(f"{BASE_MODULE}.run") as mock_run, patch(
            f"{BASE_MODULE}.print"
        ) as mock_print:
            self.test_ns.check()
            # Mocked objects should be both called for each check command
            expected_calls = len(self.test_ns.check_commands)
            self.assertEqual(expected_calls, mock_run.call_count)
            self.assertEqual(expected_calls, mock_print.call_count)

    def test_create(self) -> None:
        with patch(f"{BASE_MODULE}.run") as mock_run:
            self.test_ns.create()
            self.assertEqual(1, mock_run.call_count)

    def test_create_devices_and_address(self) -> None:
        with patch(f"{BASE_MODULE}.run") as mock_run, patch(
            f"{BASE_MODULE}.Namespace.exec_in_ns"
        ) as mock_exec_ns:
            self.test_ns.create_devices_and_address()
            # Only 1 non loopback interface - 2 calls to create int + move to ns
            self.assertEqual(2, mock_run.call_count)
            # 3 Calls for adding the v6 and v6 prefixes + checking if it exists
            self.assertEqual(3, mock_exec_ns.call_count)

    def test_delete(self) -> None:
        with patch(f"{BASE_MODULE}.LOG.info") as mock_log:
            self.test_ns.delete()
            self.assertEqual(1, mock_log.call_count)

    def test_valid_class(self) -> None:
        self.assertTrue("left", self.test_ns.name)

    def test_oob_addrs(self) -> None:
        expected = [IPv6Interface("fddd::1/64"), IPv4Interface("10.255.255.1/24")]
        self.assertEqual(expected, self.test_ns.oob_addrs())
