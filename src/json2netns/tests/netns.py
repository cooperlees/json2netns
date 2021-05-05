#!/usr/bin/env python3

import unittest
from pathlib import Path


from json2netns.netns import Namespace, load_config

BASE_PATH = Path(__file__).parent.parent.resolve()
SAMPLE_JSON_CONF_PATH = BASE_PATH / "sample.json"


class NetNSTests(unittest.TestCase):
    def setUp(self) -> None:
        config = load_config(SAMPLE_JSON_CONF_PATH)
        for ns_name, ns_conf in config["namespaces"].items():
            self.test_ns = Namespace(ns_name, ns_conf, config)
            break

    def test_valid_class(self) -> None:
        self.assertTrue("left", self.test_ns.name)
