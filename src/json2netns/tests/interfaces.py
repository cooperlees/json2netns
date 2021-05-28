import unittest
from ipaddress import ip_interface
from unittest.mock import patch

from json2netns.interfaces import (
    Interface,
    MacVlan,
    Veth,
)


BASE_MODULE = "json2netns.interfaces"


class InterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prefixes = ["6.9.6.9/31", "69::69/64"]
        self.interface = Interface()
        self.mac_vlan = MacVlan("macvlan0", "eth0", self.prefixes)
        self.veth = Veth("veth0", "veth69", self.prefixes)

    def test_convert_to_ip_interface(self) -> None:
        prefixes = []
        self.assertEqual(prefixes, self.interface._convert_to_ip_interfaces(prefixes))

        expected = [ip_interface(i) for i in self.prefixes]
        self.assertEqual(
            expected, self.interface._convert_to_ip_interfaces(self.prefixes)
        )

    def test_delete(self) -> None:
        with patch(f"{BASE_MODULE}.run") as mock_run:
            self.assertIsNone(self.interface.delete())
            self.assertEqual(1, mock_run.call_count)
