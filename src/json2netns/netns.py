import logging
from ipaddress import IPv4Network, IPv6Network, ip_network
from json import load
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Dict, List, Sequence, Union


IP = "/usr/sbin/ip"
IPNetwork = Union[IPv4Network, IPv6Network]
LOG = logging.getLogger(__name__)


class Namespace:
    def __init__(self, name: str, ns_config: Dict, config: Dict) -> None:
        self.name = name
        self.config = config
        self.id = ns_config["id"]
        self.oob = ns_config["oob"]
        self.interfaces = ns_config["interfaces"]
        self.routes = ns_config["routes"]

    def _create_or_delete(self, delete: bool, check: bool = True) -> CompletedProcess:
        """Create or delete the entire netns"""
        ns_path = Path(f"/run/netns/{self.name}")
        if not delete and not ns_path.exists():
            LOG.info(f"Namespace {self.name} already exists ...")
            return None
        elif delete and ns_path.exists():
            LOG.info(f"Namespace {self.name} does not exist ...")
            return None

        op = "del" if delete else "add"
        cp = run(*[f"{IP}", "netns", op, self.ns_name], check=check)
        LOG.info(f"Successfully '{op}'ed {self.name} namespace")
        return cp

    def create(self, delete: bool = False) -> None:
        self._create_or_delete(delete=False)

    def delete(self) -> None:
        self._create_or_delete(delete=True)

    def create_device(self) -> None:
        """Create virtual network device and assign to the netns"""
        pass

    def exec_in_ns(self, cmd: Sequence[str], check: bool = True) -> CompletedProcess:
        """Run command from inside the netns"""
        ns_cmd = [IP, "netns", "exec", self.name]
        ns_cmd.extend(cmd)
        cp = run(*ns_cmd, check=check)
        LOG.debug(f"Finished running '{' '.join(ns_cmd)}' {self.name} namespace")
        return cp

    def oob_addrs(self) -> List[IPNetwork]:
        if not self.config["oob"] and not self.config["oob"]["prefixes"]:
            raise ValueError("JSON config does not have valid OOB Prefix(es).")

        prefixes = []
        for prefix in self.config["oob"]["prefixes"]:
            network_obj = ip_network(prefix)
            prefixes.append(network_obj + self.id)

        return prefixes

    def route_add(self) -> None:
        """Add any needed static routes in netns"""
        pass


def load_config(conf_path: Path) -> Dict:
    with conf_path.open("rb") as cfp:
        return load(cfp)
