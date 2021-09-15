#!/usr/bin/env python3

import logging
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from typing import List
from unittest.mock import patch

from json2netns.config import Config
from json2netns.route import Route

BASE_PATH = Path(__file__).parent.parent.resolve()
BASE_MODULE = "json2netns.route"
LOG = logging.getLogger(__name__)
SAMPLE_JSON_CONF_PATH = BASE_PATH / "sample.json"

route_list: List = []


def log_cmds_ran(*args, **kwargs) -> CompletedProcess:
    """Useful function to use with patch() to see what's being ran"""
    LOG.debug(f"CMD ARGS: {args} - {kwargs}")
    # Always return 0 - Naturally return non 0 for errors
    return CompletedProcess(args, 0)


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(SAMPLE_JSON_CONF_PATH).load()
        # Initialize routes
        self.route_initialize()

    def route_initialize(self) -> None:
        self.route_list = []
        for ns_name, ns_conf in self.config["namespaces"].items():
            for route_name, route in ns_conf["routes"].items():
                # Initialize route obj
                route_obj = Route(
                    route_name,
                    ns_name,
                    route["dest_prefix"],
                    route["next_hop_ip"],
                    route["egress_if_name"],
                )
                # create a list of known good route objects to use for testing
                self.route_list.append(route_obj)

        # Create bad route objects for testing
        self.mismatch_route_obj = Route(
            "mismatch_route", "bad_ns", "10.6.9.5/32", "fd00::1", "eth69"
        )
        self.bad_dest_obj = Route(
            "bad__dest_route", "bad_ns", "10.6.9.5/69", "10.1.1.1", "eth69"
        )

        self.bad_nexthop_obj = Route(
            "bad_nexthop_route", "bad_ns", "192.168.1.0/32", "192.168.1.6969", "eth69"
        )

    def test_proto_match_validated(self) -> None:
        # validate protocols match
        for route in self.route_list:
            self.assertTrue(route._Route__proto_match_validated())

        # validate protocols don't match
        self.assertFalse(self.mismatch_route_obj._Route__proto_match_validated())

    def test_route_validated(self) -> None:
        # validate routes are valid
        for route in self.route_list:
            self.assertTrue(route._Route__route_validated())

        # validate bad destination is invalid
        with self.assertRaises(ValueError):
            self.bad_dest_obj._Route__proto_match_validated()

        # validate bad next-hop in invalid
        with self.assertRaises(ValueError):
            self.bad_nexthop_obj._Route__proto_match_validated()

    def test_route_exists(self) -> None:
        with patch(f"{BASE_MODULE}.check_output") as mock_check_output:
            # Use first route in sample.json to test -> 10.6.9.6 via 10.1.1.2
            # Route that isn't in table
            mock_check_output.return_value = b"10.1.1.0/24 dev ens192"
            self.assertFalse(self.route_list[0].route_exists())
            # Host route that is in table
            mock_check_output.return_value = b"10.6.9.6/32 via 10.1.1.2"
            self.assertTrue(self.route_list[0].route_exists())

            # Use second route in sample.json to test v6 non-host -> fd00:6::/64 via fd00::1
            # v6 route that isn't in the table
            mock_check_output.return_value = b"fd00::64/64 dev ens192"
            self.assertFalse(self.route_list[1].route_exists())
            # v6 route that is in table
            mock_check_output.return_value = b"fd00:6::/64 dev ens192"
            self.assertTrue(self.route_list[1].route_exists())

    def test_get_route(self) -> None:
        # Use first host route in sample.json to test -> 10.6.9.6 via 10.1.1.2
        # Checks within this method are done above, thus mocked
        with patch.object(
            Route, "_Route__proto_match_validated", return_value=True
        ), patch.object(
            Route, "_Route__route_validated", return_value=True
        ), patch.object(
            Route, "route_exists", return_value=False
        ):
            self.assertEqual(
                self.route_list[0].get_route(),
                ["/usr/sbin/ip", "route", "add", "10.6.9.6/32", "via", "10.1.1.2"],
            )
