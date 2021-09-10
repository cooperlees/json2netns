#!/usr/bin/env python3

import logging
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from typing import List

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
        print(self.config)
        # Initialize routes
        self.route_initialize()

    def route_initialize(self) -> None:
        self.route_list = []
        for ns_name, ns_conf in self.config["namespaces"].items():
            for route_name, route in ns_conf["routes"].items():
                # ### DEBUGGING: Delete before committing ###
                print(route)
                # Initialize route obj
                route_obj = Route(
                    route_name,
                    ns_name,
                    route["dest_prefix"],
                    route["next_hop_ip"],
                    route["egress_if_name"],
                )
                # create a list of known good route objects to use
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
            self.assertIs(
                route._Route__proto_match_validated(),
                True,
            )

        # validate protocols don't match
        self.assertIs(
            self.mismatch_route_obj._Route__proto_match_validated(),
            False,
        )
        # with self.assertRaises(ValueError):
        #     self.mismatch_route_obj._Route__proto_match_validated()

    def test_route_validated(self) -> None:
        # validate routes are valid
        for route in self.route_list:
            self.assertIs(
                route._Route__route_validated(),
                True,
            )

        # validate bad destination is invalid
        with self.assertRaises(ValueError):
            self.bad_dest_obj._Route__proto_match_validated()

        # validate bad next-hop in invalid
        with self.assertRaises(ValueError):
            self.bad_nexthop_obj._Route__proto_match_validated()

    def test_route_exists(self) -> None:
        pass

    def test_get_route(self) -> None:
        pass
