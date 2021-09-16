import logging
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from subprocess import check_output
from typing import List

from json2netns.consts import DEFAULT_IP


LOG = logging.getLogger(__name__)

IP = DEFAULT_IP


@dataclass
class Route:
    name: str
    netns_name: str
    dest_prefix: str
    next_hop_ip: str
    egress_if_name: str

    # TODO Add support for IPv4 via IPv6 next hops (should probably open separate issue)
    def __proto_match_validated(self) -> bool:
        """Check to make sure the destination IP and next-hop match protocols (v4/v6)"""
        if ip_network(self.dest_prefix).version == ip_address(self.next_hop_ip).version:
            return True
        else:
            return False

    def __route_validated(self) -> bool:
        """Check to make sure all elements exist that are needed for a valid route
        , then validate those elements"""
        if self.dest_prefix and (self.next_hop_ip or self.egress_if_name):
            # Check for bad destination prefix, if so skip route installation
            try:
                ip_network(self.dest_prefix)
            except ValueError:
                LOG.error(f"{self.dest_prefix} is not a valid network address.")
                return False
        if self.next_hop_ip:
            # Check if next hop IP is specified, if so check for bad next hop address
            # and skip route installation
            try:
                ip_address(self.next_hop_ip)
            except ValueError:
                LOG.error(f"{self.next_hop_ip} is not a valid ip address.")
                return False
        return True

    def route_exists(self) -> bool:
        """Checks if route exists already (maintain idempotency)"""
        route_4_cmd = [
            IP,
            "netns",
            "exec",
            self.netns_name,
            IP,
            "route",
            "show",
        ]
        route_6_cmd = [
            IP,
            "netns",
            "exec",
            self.netns_name,
            IP,
            "-6",
            "route",
            "show",
        ]

        cp = (check_output(route_4_cmd)).decode("utf-8")
        cp = cp + (check_output(route_6_cmd)).decode("utf-8")

        # Linux outputs host routes without /32 subnet mask
        # Search for /32 in route, if doesn't exist search in table, return result
        if self.dest_prefix.find("/32") == -1:
            if cp.find(self.dest_prefix) == -1:
                return False
            else:
                return True
        # If /32 exists in route, strip it, search in table, return result
        else:
            if cp.find(self.dest_prefix.strip(r"\/32")) == -1:
                return False
            else:
                return True

    def get_route(self) -> List[str]:
        """Generate cmd list for use with ns class"""
        # check that it's a valid destination address and next hop format
        if not self.__route_validated():
            LOG.error(
                f"Route validation failed, skipping installation of {self.dest_prefix}"
            )
            return []
        # check that the destination and next hop are members of same protocol (v4/v6)
        # Add support for IPv4 via IPv6 next hops (should probably open separate issue)
        if not self.__proto_match_validated():
            LOG.error(
                f"Destination and next hop protocol mismatch, skipping installation of {self.dest_prefix}"
            )
            return []
        # check to see if the destination prefix exists in the namespace route table
        if self.route_exists():
            LOG.error(
                f"Route already exists in table, skipping installation of {self.dest_prefix}"
            )
            return []
        # We have checked the route doesn't exist, generate cmd list:
        # send route with next hop ip and next hop interface
        if self.next_hop_ip and self.egress_if_name:
            cmd = [
                IP,
                "route",
                "add",
                self.dest_prefix,
                "via",
                self.next_hop_ip,
                "dev",
                self.egress_if_name,
            ]

        elif self.dest_prefix:
            # send route with next hop ip
            cmd = [
                IP,
                "route",
                "add",
                self.dest_prefix,
                "via",
                self.next_hop_ip,
            ]

        elif self.egress_if_name:
            # send route with next hop dev
            cmd = [
                IP,
                "route",
                "add",
                self.dest_prefix,
                "dev",
                self.egress_if_name,
            ]
        return cmd
