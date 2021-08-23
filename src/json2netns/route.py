import logging
from ipaddress import ip_address, ip_network
from subprocess import check_output, run, PIPE
from typing import Dict, List

from json2netns.consts import DEFAULT_IP


LOG = logging.getLogger(__name__)


class Route:
    IP = DEFAULT_IP

    def __init__(self, netns_name: str, name: str, route: Dict) -> None:
        self.name = name
        self.netns_name = netns_name
        self.route = route

    def __proto_match_validated(self, route_test: Dict) -> bool:
        """Check to make sure the destination IP and next-hop match protocols (v4/v6)"""
        if (
            ip_network(route_test["dest_prefix"]).version
            == ip_address(route_test["next_hop_ip"]).version
        ):
            return True
        else:
            return False

    def __route_validated(self, route_test: Dict) -> bool:
        """Check to make sure all elements exist that are needed for a valid route
        , then validate those elements"""
        if (route_test["dest_prefix"]) and (
            route_test["next_hop_ip"] or route_test["exit_if_name"]
        ):
            # Check for bad destination prefix, if so skip route installation
            try:
                ip_network(route_test["dest_prefix"])
            except ValueError:
                LOG.error(
                    f"{route_test['dest_prefix']} is not a valid network address."
                )
                return False
        if route_test["next_hop_ip"]:
            # Check if next hop IP is specified, if so check for bad next hop address
            # and skip route installation
            try:
                ip_address(route_test["next_hop_ip"])
            except ValueError:
                LOG.error(f"{route_test['next_hop_ip']} is not a valid ip address.")
                return False
        return True

    def route_exists(self, route_prefix: str) -> bool:
        """Checks if route exists already (maintain idempotency)"""
        route_4_cmd = [
            self.IP,
            "netns",
            "exec",
            self.netns_name,
            self.IP,
            "route",
            "show",
        ]
        route_6_cmd = [
            self.IP,
            "netns",
            "exec",
            self.netns_name,
            self.IP,
            "-6",
            "route",
            "show",
        ]

        cp = (check_output(route_4_cmd)).decode("utf-8")
        cp = cp + (check_output(route_6_cmd)).decode("utf-8")
        if cp.find(route_prefix) == -1:
            return False
        else:
            return True

    def get_route(self) -> List:
        """Generate cmd list for use with ns class"""
        # check that it's a valid destination address and next hop format
        if not self.__route_validated(self.route):
            LOG.error(
                f"Route validation failed, skipping installation of {self.route['dest_prefix']}"
            )
            return []
        # check that the destination and next hop are members of same protocol (v4/v6)
        if not self.__proto_match_validated(self.route):
            LOG.error(
                f"Destination and next hop protocol mismatch, skipping installation of {self.route['dest_prefix']}"
            )
            return []
        # check to see if the destination prefix exists in the namespace route table
        if self.route_exists(self.route["dest_prefix"]):
            LOG.error(f"Route already exists in table, skipping route")
            return []
        # We have checked the route doesn't exist, generate cmd list:
        # send route with next hop ip and next hop interface
        if ["next_hop_ip"] and self.route["exit_if_name"]:
            cmd = [
                self.IP,
                "route",
                "add",
                self.route["dest_prefix"],
                "via",
                self.route["next_hop_ip"],
                "dev",
                self.route["exit_if_name"],
            ]

        elif self.route["next_hop_ip"]:
            # send route with next hop ip
            cmd = [
                self.IP,
                "route",
                "add",
                self.route["dest_prefix"],
                "via",
                self.route["next_hop_ip"],
            ]

        elif self.route["exit_if_name"]:
            # send route with next hop dev
            cmd = [
                self.IP,
                "route",
                "add",
                self.route["dest_prefix"],
                "dev",
                self.route["exit_if_name"],
            ]
        return cmd
