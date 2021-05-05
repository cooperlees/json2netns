#!/usr/bin/env python3

import unittest


from json2netns.tests.netns import NetNSTests  # noqa: F401


import json2netns.main


class MainTests(unittest.TestCase):
    def test_main(self) -> None:
        self.assertEqual(0, json2netns.main.main())


if __name__ == "__main__":
    unittest.main()
