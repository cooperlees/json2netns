import unittest
from unittest.mock import patch

from json2netns.interfaces import (
    Interface,
    MacVlan,
    Veth,
)


BASE_MODULE = "json2netns.interfaces"


class InterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.interface = Interface()
        self.mac_vlan = MacVlan("macvlan0", "eth0")
        self.veth = Veth("veth0", "veth69")

    def test_delete(self) -> None:
        with patch(f"{BASE_MODULE}.run") as mock_run:
            self.assertIsNone(self.interface.delete())
            self.assertEqual(1, mock_run.call_count)
