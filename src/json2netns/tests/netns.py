#!/usr/bin/env python3

import logging
from subprocess import CompletedProcess
import unittest
from copy import deepcopy
from ipaddress import IPv4Interface, IPv6Interface
from pathlib import Path
from unittest.mock import patch

from json2netns.config import Config
from json2netns.netns import Namespace, setup_all_veths, setup_global_oob

BASE_PATH = Path(__file__).parent.parent.resolve()
BASE_MODULE = "json2netns.netns"
BASE_INT_MODULE = "json2netns.interfaces"
LOG = logging.getLogger(__name__)
SAMPLE_JSON_CONF_PATH = BASE_PATH / "sample.json"


def log_cmds_ran(*args, **kwargs) -> CompletedProcess:
    """Useful function to use with patch() to see what's being ran"""
    LOG.debug(f"CMD ARGS: {args} - {kwargs}")
    # Always return 0 - Naturally return non 0 for errors
    return CompletedProcess(args, 0)


class NetNSTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(SAMPLE_JSON_CONF_PATH).load()
        for ns_name, ns_conf in self.config["namespaces"].items():
            self.test_ns = Namespace(ns_name, ns_conf, self.config)
            break

    def test_bad_id(self) -> None:
        bad_config = deepcopy(self.config)
        bad_config["namespaces"]["left"]["id"] = 0
        with self.assertRaises(ValueError):
            Namespace("bad_id", bad_config["namespaces"]["left"], bad_config)

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
        with patch(f"{BASE_MODULE}.run") as mock_run, patch(
            f"{BASE_MODULE}.Path.exists", lambda _: False
        ):
            self.test_ns.create()
            self.assertEqual(1, mock_run.call_count)

    def test_delete(self) -> None:
        with patch(f"{BASE_MODULE}.run") as mock_run, patch(
            f"{BASE_MODULE}.Path.exists", lambda _: True
        ):
            self.test_ns.delete()
            self.assertEqual(1, mock_run.call_count)

    def test_setup_links(self) -> None:
        with patch(f"{BASE_INT_MODULE}.run") as mock_run:
            # with patch(f"{BASE_INT_MODULE}.run", log_cmds_ran):
            self.test_ns.setup_links()
            # 11 Calls to run():
            # For each lo prefix + veth
            # - Check if exists
            # - Create (veth only - no create lo)
            # - 2 calls for adding the v6 and v6 prefixes
            # - Setting interface 'up'
            # - Move interface to netns
            self.assertEqual(11, mock_run.call_count)

    def test_valid_class(self) -> None:
        self.assertTrue("left", self.test_ns.name)

    def test_oob_addrs(self) -> None:
        expected = [IPv6Interface("fddd::1/64"), IPv4Interface("10.255.255.1/24")]
        self.assertEqual(expected, self.test_ns.oob_addrs())

    def test_setup_all_veths(self) -> None:
        # This test can not be ran in an env where a left0 interface can exist
        ns_dict = {"left": self.test_ns}
        with patch(f"{BASE_INT_MODULE}.run") as mock_int_run:
            setup_all_veths(ns_dict)
            # 2 exists calls and 1 create
            self.assertEqual(3, mock_int_run.call_count)

    def test_setup_global_oob(self) -> None:
        test_ns_dict = {"test_ns": deepcopy(self.test_ns)}
        # Test when we want a global OOB interface
        with patch(f"{BASE_INT_MODULE}.run") as mock_run:
            self.assertIsNone(setup_global_oob("unittest0", test_ns_dict, self.config))
            self.assertEqual(4, mock_run.call_count)

        # Test when we don't want a global OOB interface
        test_ns_dict["test_ns"].oob = False
        with patch(f"{BASE_MODULE}.LOG.debug") as mock_log_debug:
            self.assertIsNone(setup_global_oob("unittest1", test_ns_dict, self.config))
            self.assertEqual(1, mock_log_debug.call_count)
