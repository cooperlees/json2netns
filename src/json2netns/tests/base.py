#!/usr/bin/env python3.7

import unittest


# from json2netns.tests.x_tests import XTests  # noqa: F401


import json2netns.main


class MainTests(unittest.TestCase):
    def test_main(self) -> None:
        self.assertEqual(0, json2netns.main.main())


if __name__ == "__main__":
    unittest.main()
