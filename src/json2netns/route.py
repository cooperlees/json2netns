import logging
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from subprocess import check_output
from typing import List

from json2netns.consts import DEFAULT_IP


LOG = logging.getLogger(__name__)

IP = DEFAULT_IP


# TODO: Swap the "route/attributes" dict for properties of the "Route" object or make a RouteAttributes named tuple OR dataclass
#   Why? Stricter typing than a dict (Can name own types on these ex. IP_ADDRESS)
#       From a JSON config we can use **kwargs to construct the objects nicely
@dataclass
class Route:
    name: str
    netns_name: str
    dest_prefix: str
    next_hop_ip: str
    egress_if_name: str


def __proto_match_validated(dest_prefix: str, next_hop_ip: str) -> bool:
    """Check to make sure the destination IP and next-hop match protocols (v4/v6)"""
    if ip_network(dest_prefix).version == ip_address(next_hop_ip).version:
        return True
    else:
        return False


def __route_validated(dest_prefix: str, next_hop_ip: str, egress_if_name: str) -> bool:
    """Check to make sure all elements exist that are needed for a valid route
    , then validate those elements"""
    if dest_prefix and (next_hop_ip or egress_if_name):
        # Check for bad destination prefix, if so skip route installation
        try:
            ip_network(dest_prefix)
        except ValueError:
            LOG.error(f"{dest_prefix} is not a valid network address.")
            return False
    if next_hop_ip:
        # Check if next hop IP is specified, if so check for bad next hop address
        # and skip route installation
        try:
            ip_address(next_hop_ip)
        except ValueError:
            LOG.error(f"{next_hop_ip} is not a valid ip address.")
            return False
    return True


def route_exists(dest_prefix: str, netns_name: str) -> bool:
    """Checks if route exists already (maintain idempotency)"""
    route_4_cmd = [
        IP,
        "netns",
        "exec",
        netns_name,
        IP,
        "route",
        "show",
    ]
    route_6_cmd = [
        IP,
        "netns",
        "exec",
        netns_name,
        IP,
        "-6",
        "route",
        "show",
    ]

    cp = (check_output(route_4_cmd)).decode("utf-8")
    cp = cp + (check_output(route_6_cmd)).decode("utf-8")
    if cp.find(dest_prefix) == -1:
        return False
    else:
        return True


def get_route(route_object: Route) -> List[str]:
    """Generate cmd list for use with ns class"""
    # check that it's a valid destination address and next hop format
    if not __route_validated(
        route_object.dest_prefix, route_object.next_hop_ip, route_object.egress_if_name
    ):
        LOG.error(
            f"Route validation failed, skipping installation of {route_object.dest_prefix}"
        )
        return []
    # check that the destination and next hop are members of same protocol (v4/v6)
    # Add support for IPv4 via IPv6 next hops (should probably open separate issue)
    if not __proto_match_validated(route_object.dest_prefix, route_object.next_hop_ip):
        LOG.error(
            f"Destination and next hop protocol mismatch, skipping installation of {route_object.dest_prefix}"
        )
        return []
    # check to see if the destination prefix exists in the namespace route table
    if route_exists(route_object.dest_prefix, route_object.netns_name):
        LOG.error(
            f"Route already exists in table, skipping installation of {route_object.dest_prefix}"
        )
        return []
    # We have checked the route doesn't exist, generate cmd list:
    # send route with next hop ip and next hop interface
    if route_object.next_hop_ip and route_object.egress_if_name:
        cmd = [
            IP,
            "route",
            "add",
            route_object.dest_prefix,
            "via",
            route_object.next_hop_ip,
            "dev",
            route_object.egress_if_name,
        ]

    elif route_object.next_hop_ip:
        # send route with next hop ip
        cmd = [
            IP,
            "route",
            "add",
            route_object.dest_prefix,
            "via",
            route_object.next_hop_ip,
        ]

    elif route_object.egress_if_name:
        # send route with next hop dev
        cmd = [
            IP,
            "route",
            "add",
            route_object.dest_prefix,
            "dev",
            route_object.egress_if_name,
        ]
    return cmd
