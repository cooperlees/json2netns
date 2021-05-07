#!/usr/bin/env python3

import argparse
import asyncio
import unittest
from unittest.mock import patch
from pathlib import Path

import json2netns.main
from json2netns.config import Config
from json2netns.tests.netns import InterfaceTests, NetNSTests  # noqa: F401


BASE_PATH = Path(__file__).parent.parent.resolve()
SAMPLE_CONF = BASE_PATH / "sample.json"


class MainTests(unittest.TestCase):
    def test_amiroot(self) -> None:
        self.assertFalse(json2netns.main.amiroot())

    def test_async_main_check(self) -> None:
        ns = argparse.Namespace(
            action="check", config=str(SAMPLE_CONF), debug=True, workers=1
        )
        with patch("json2netns.netns.Namespace.check") as mock_check, patch(
            "json2netns.main.print"
        ) as mock_print, patch("json2netns.main.amiroot", returm_value=True):
            self.assertEqual(0, asyncio.run(json2netns.main.async_main(ns)))
            self.assertEqual(2, mock_check.call_count)
            self.assertEqual(3, mock_print.call_count)

    def test_main(self) -> None:
        ns = argparse.Namespace(
            action="check", config=str(SAMPLE_CONF), debug=True, workers=1
        )
        with patch(
            "argparse.ArgumentParser.parse_args", return_value=ns
        ) as mock_pa, patch(
            "json2netns.main.async_main", return_value=0
        ) as mock_async_main:
            self.assertEqual(0, json2netns.main.main())
            self.assertEqual(1, mock_async_main.call_count)
            self.assertEqual(1, mock_pa.call_count)

    def test_bad_args(self) -> None:
        ns = argparse.Namespace(
            action="check", config=str(BASE_PATH / "not_there"), debug=True, workers=1
        )
        self.assertEqual(1, json2netns.main.validate_args(ns))

        ns.action = "cooper_fuck_yes"
        ns.config = str(SAMPLE_CONF)
        self.assertEqual(2, json2netns.main.validate_args(ns))


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(SAMPLE_CONF)

    def test_load_config(self) -> None:
        self.assertTrue(isinstance(self.config.load(), dict))


if __name__ == "__main__":
    unittest.main()
