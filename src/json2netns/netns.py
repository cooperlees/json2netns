import logging
from ipaddress import IPv4Interface, IPv6Interface, ip_interface, ip_network
from json import load
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Dict, List, Sequence, Union


IPInterface = Union[IPv4Interface, IPv6Interface]
LOG = logging.getLogger(__name__)


class Namespace:
    IP = "/usr/sbin/ip"
    check_commands = {
        "## Addresses": (IP, "addr", "show"),
        "## Routes (v4)": (IP, "route", "show"),
        "## Routes (v6)": (IP, "-6", "route", "show"),
    }

    def __init__(self, name: str, ns_config: Dict, config: Dict) -> None:
        self.name = name
        self.config = config
        self.id = ns_config["id"]
        self.interfaces = ns_config["interfaces"]
        self.routes = ns_config["routes"]

        self.oob = ns_config["oob"]
        self.oob_prefixes = None
        if self.oob:
            self.oob_prefixes = [
                ip_network(prefix) for prefix in config["oob"]["prefixes"]
            ]

    def _create_or_delete(self, delete: bool, check: bool = True) -> CompletedProcess:
        """Create or delete the entire netns"""
        ns_path = Path(f"/run/netns/{self.name}")
        if not delete and ns_path.exists():
            LOG.info(f"Namespace {self.name} already exists ...")
            return None
        elif delete and not ns_path.exists():
            LOG.info(f"Namespace {self.name} does not exist ...")
            return None

        op = "del" if delete else "add"
        cp = run(f"{self.IP}", "netns", op, self.name, check=check)
        LOG.info(f"Successfully '{op}'ed {self.name} namespace")
        return cp

    def _link_add(
        self, name: str, int_type: str, *, peer_name: str = "", physical_int: str = ""
    ) -> None:
        cmd = [self.IP, "link", "add", name]
        if int_type == "macvlan":
            cmd.extend(["link", physical_int, "type", "macvlan", "mode", "bridge"])
        elif int_type == "veth":
            cmd.extend(["type", "veth", "peer", "name", peer_name])
        else:
            raise ValueError(f"{int_type} is not supported yet ... PR time?")
        run(*cmd, check=True)

        link_set_cmd = [self.IP, "link", "set", name, "netns", self.name]
        run(*link_set_cmd, check=True)
        LOG.info(f"Successfully created + added {name} to {self.name} namespace")

    def check(self) -> None:
        for header, cmd in self.check_commands.items():
            print(header)
            self.exec_in_ns(cmd, check=False)

    def create(self, delete: bool = False) -> None:
        self._create_or_delete(delete=False)

    def delete(self) -> None:
        self._create_or_delete(delete=True)

    def create_devices(self) -> None:
        """Create virtual network device and assign to the netns"""
        for int_name, int_config in self.interfaces:
            if int_config["type"] == "loopback":
                continue

            peer_name = int_config["peer_name"] if "peer_name" in int_config else ""
            physical_int = (
                self.config["physical_int"] if "physical_int" in self.config else ""
            )
            self._link_add(
                int_config["type"], peer_name=peer_name, physical_int=physical_int
            )

    def create_oob(self) -> None:
        """If configured, add a OOB device to connect to global namespace + bridge with a physical interface"""
        if not self.oob:
            LOG.debug(f"No oob configred for {self.name}")
            return

        oob_int_name = f"oob{self.id}"
        print(f"Finish oob setup - {oob_int_name}")  # COOPER

    def exec_in_ns(self, cmd: Sequence[str], check: bool = True) -> CompletedProcess:
        """Run command from inside the netns"""
        ns_cmd = [self.IP, "netns", "exec", self.name]
        ns_cmd.extend(cmd)
        cp = run(*ns_cmd, check=check)
        LOG.debug(f"Finished running '{' '.join(ns_cmd)}' {self.name} namespace")
        return cp

    def oob_addrs(self) -> List[IPInterface]:
        if not self.oob:
            LOG.error(f"No oob asked to be set on {self.name} namespace")
            return []
        if not self.oob_prefixes:
            LOG.error(f"No oob prefiex to apply to {self.name}")
            return []

        interfaces = []
        for oob_net in self.oob_prefixes:
            interfaces.append(
                ip_interface(
                    f"{str(oob_net.network_address + self.id)}/{int(oob_net.prefixlen)}"
                )
            )

        return interfaces

    def route_add(self) -> None:
        """Add any needed static routes in netns"""
        pass

    def bootstrap(self) -> None:
        """Cordination function to create all the namespace elements"""
        pass


def load_config(conf_path: Path) -> Dict:
    with conf_path.open("rb") as cfp:
        return load(cfp)
