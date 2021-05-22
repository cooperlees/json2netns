from ipaddress import IPv4Interface, IPv6Interface
from typing import Union


DEFAULT_IP = "/usr/sbin/ip"
GLOBAL_OOB_INTERFACE = "oob0"
IPInterface = Union[IPv4Interface, IPv6Interface]
VALID_ACTIONS = {"create", "delete", "check"}
VALID_SORTED_ACTIONS = sorted(VALID_ACTIONS)
