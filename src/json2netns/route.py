from ipaddress import ip_address, ip_network
from typing import Dict, List
import logging
from subprocess import check_output

from json2netns.consts import DEFAULT_IP


LOG = logging.getLogger(__name__)


class Route:
    IP = DEFAULT_IP

    def __init__(self, netns_name: str, name: str, route: Dict) -> None:
        self.name = name
        self.netns_name = netns_name
        self.route = route

    def __validate_routes(self, route_test: Dict) -> int:
        """Check to make sure all elements exist that are needed for a valid route, then validate those elements"""
        if (route_test["dest_prefix"]) and (
            route_test["next_hop_ip"] or route_test["exit_if_name"]
        ):
            # Check for bad destination prefix, if so skip route installation
            try:
                ip_network(route_test["dest_prefix"])
            except ValueError:
                LOG.error(
                    f"{route_test['dest_prefix']} is not a valid network address, please check config"
                )  # convert to error log
                return 1
            # Check if a next hop IP if specified, if so check for bad next hop address and skip route installation
        if route_test["next_hop_ip"]:
            try:
                ip_address(route_test["next_hop_ip"])
            except ValueError:
                LOG.error(
                    f"{route_test['next_hop_ip']} is not a valid ip address, please check config"
                )  # convert to error log
                return 1
        return 0

    def __route_exists(self, route_prefix: str) -> bool:
        """Checks if route exists already (maintain idempotency)"""
        route_cmd = [
            self.IP,
            "netns",
            "exec",
            self.netns_name,
            self.IP,
            "route",
            "show",
            route_prefix,
        ]
        cp = (check_output(route_cmd)).decode("utf-8")
        if cp == "":
            return 0
        else:
            LOG.info(f"{route_prefix} already exists in route table, skipping...")
            return 1

    def get_route(self) -> List:
        """Generate cmd list for use with ns class"""
        if self.__validate_routes(self.route) == 0:
            # check that it's a valid destination address and next hop format
            if self.__route_exists(self.route["dest_prefix"]) == 0:
                # We have checked the route doesn't exist, generate cmd list
                if ["next_hop_ip"] and self.route["exit_if_name"]:
                    # send route with next hop ip and next hop interface
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
