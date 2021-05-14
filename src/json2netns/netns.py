import logging
from ipaddress import IPv4Interface, IPv6Interface, ip_interface, ip_network
from pathlib import Path
from subprocess import CompletedProcess, DEVNULL, PIPE, run
from typing import Dict, List, Optional, Sequence, Union


DEFAULT_IP = "/usr/sbin/ip"
IPInterface = Union[IPv4Interface, IPv6Interface]
LOG = logging.getLogger(__name__)


class Namespace:
    IP = DEFAULT_IP
    check_commands = {
        "## Addresses": (IP, "addr", "show"),
        "## Routes (v4)": (IP, "route", "show"),
        "## Routes (v6)": (IP, "-6", "route", "show"),
    }

    def __init__(self, name: str, ns_config: Dict, config: Dict) -> None:
        self.name = name
        self.ns_path = Path(f"/run/netns/{self.name}")
        self.config = config
        if ns_config["id"] < 1:
            # The global oob and other resources will always be 0
            raise ValueError("A namespace ID must be > 0")
        self.id = ns_config["id"]
        self.interfaces = ns_config["interfaces"]
        self.routes = ns_config["routes"]

        self.oob = ns_config["oob"]
        self.oob_prefixes = None
        if self.oob:
            self.oob_prefixes = [
                ip_network(prefix) for prefix in config["oob"]["prefixes"]
            ]

    def _create_or_delete(
        self, delete: bool, check: bool = True
    ) -> Optional[CompletedProcess]:
        """Create or delete the entire netns"""
        if not delete and self.ns_path.exists():
            LOG.info(f"{self.name} namespace already exists ...")
            return None
        elif delete and not self.ns_path.exists():
            LOG.info(f"{self.name} namespace does not exist ...")
            return None

        op = "delete" if delete else "add"
        d = "d" if delete else "ed"
        cp = run((f"{self.IP}", "netns", op, self.name), check=check)
        LOG.info(f"Successfully {op}{d} {self.name} namespace")
        return cp

    # TODO: Use Interface Objects here
    def _link_add(
        self,
        link_name: str,
        int_type: str,
        *,
        peer_name: str = "",
        physical_int: str = "",
    ) -> None:
        cmd = [self.IP, "link", "add", link_name]
        if int_type == "macvlan":
            cmd.extend(["link", physical_int, "type", "macvlan", "mode", "bridge"])
        elif int_type == "veth":
            return self._link_set_ns(link_name)
        else:
            raise ValueError(f"{int_type} is not supported yet ... PR time?")

        run(cmd, check=True)
        LOG.info(f"Successfully created {link_name}")
        self._link_set_ns(link_name)

    def _link_set_ns(self, link_name: str) -> None:
        link_set_cmd = [self.IP, "link", "set", link_name, "netns", self.name]
        run(link_set_cmd, check=True)
        LOG.info(f"Moved {link_name} to {self.name} namespace")

    def _prefix_add(
        self,
        interface: str,
        prefixes: Sequence[Union[IPInterface, str]],
    ) -> None:
        """Add prefixes onto a namespace interfance"""
        for prefix in prefixes:
            cmd = [self.IP, "addr", "add", str(prefix), "dev", interface]
            self.exec_in_ns(cmd)
            LOG.info(f"Added {str(prefix)} to {interface} in {self.name} namespace")

    def check(self) -> None:
        for header, cmd in self.check_commands.items():
            print(header)
            self.exec_in_ns(cmd, check=False)

    def create(self, delete: bool = False) -> None:
        self._create_or_delete(delete=False)

    def delete(self) -> None:
        self._create_or_delete(delete=True)

    def create_devices_and_address(self) -> None:
        """Create virtual network device and assign to the netns"""
        for int_name, int_config in self.interfaces.items():
            if int_config["type"] == "loopback":
                continue

            if self.interface_exists(int_name) == 0:
                LOG.info("Skipping interface creation as {int_name} already exits")
                continue

            peer_name = int_config["peer_name"] if "peer_name" in int_config else ""
            physical_int = (
                self.config["physical_int"] if "physical_int" in self.config else ""
            )
            self._link_add(
                int_name,
                int_config["type"],
                peer_name=peer_name,
                physical_int=physical_int,
            )
            self._prefix_add(int_name, int_config["prefixes"])
            self.up_interface(int_name)

    def create_oob(self) -> None:
        """If configured, add a OOB device to connect to global namespace
        + bridge with a physical interface"""
        if not self.oob:
            LOG.debug(f"No oob configred for {self.name}")
            return

        oob_int_name = f"oob{self.id}"
        physical_int = (
            self.config["physical_int"] if "physical_int" in self.config else ""
        )
        if not physical_int:
            raise ValueError(
                f"No Physical int to bridge macvlan OOB interface with for {self.name}"
            )
        self._link_add(oob_int_name, "macvlan", physical_int=physical_int)
        oob_prefixes = self.oob_addrs()
        self._prefix_add(oob_int_name, oob_prefixes)

    def exec_in_ns(
        self, cmd: Sequence[str], check: bool = True, output: bool = True
    ) -> CompletedProcess:
        """Run command from inside the netns"""
        output_fd = None if output else DEVNULL
        ns_cmd = [self.IP, "netns", "exec", self.name]
        ns_cmd.extend(cmd)
        LOG.debug(f"Running '{' '.join(ns_cmd)}' in {self.name} namespace")
        cp = run(ns_cmd, check=check, stdout=output_fd, stderr=output_fd)
        LOG.debug(
            f"Finished running '{' '.join(ns_cmd)}' {self.name} namespace "
            + f"(returned {cp.returncode})"
        )
        return cp

    def interface_exists(self, interface: str, outside_ns: bool = False) -> int:
        """Check if a device exists"""
        cmd = [self.IP, "link", "show", "dev", interface]
        if outside_ns:
            return run(cmd, stdout=DEVNULL, stderr=DEVNULL).returncode
        else:
            return self.exec_in_ns(cmd, check=False, output=False).returncode

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

    # TODO: Add support
    def route_add(self) -> None:
        """Add any needed static routes in netns"""
        pass

    def up_interface(self, interface: str) -> None:
        up_cmd = [self.IP, "link", "set", "up", "dev", interface]
        self.exec_in_ns(up_cmd, output=False)
        LOG.debug(f"Set '{interface}' interface up")

    def setup_loopback(self, loopback_int_name: str = "lo") -> None:
        """Set loopback up (always) + add prefixes if desired"""
        self.up_interface(loopback_int_name)
        if (
            loopback_int_name not in self.interfaces
            and "prefixes" not in self.interfaces[loopback_int_name]
        ):
            return
        prefixes = []
        for prefix in self.interfaces[loopback_int_name]["prefixes"]:
            prefixes.append(ip_interface(prefix))
        if prefixes:
            self._prefix_add(loopback_int_name, prefixes)

    def setup(self) -> None:
        """Cordination function to setup all the namespace elements
        - Designed to be idempotent - i.e. if it exists, move on"""
        # Create netns
        self.create()
        # Always bring loopback up
        self.setup_loopback()
        # Create links/interfaces + address them
        self.create_devices_and_address()
        # Create oob if selected
        self.create_oob()
        # Add any static routes
        self.route_add()


class Interface:
    IP = DEFAULT_IP
    name = "Interface"
    type = "Interface"

    def add_prefixes(self, prefixes: Sequence[IPInterface]) -> None:
        for prefix in prefixes:
            cmd = [self.IP, "addr", "add", str(prefix), "dev", self.name]
            run(cmd, check=True, stdout=PIPE, stderr=PIPE)

    def delete(self) -> Optional[CompletedProcess]:
        if not self.exists():
            LOG.debug(
                f"Not deleting {self.name} {self.type} interface as it does not exist ..."
            )
            return None

        cmd = [self.IP, "link", "del", self.name]
        LOG.info(f"Deleting {self.type} interface {self.name}")
        return run(cmd, check=True, stdout=PIPE, stderr=PIPE)

    def exists(self) -> bool:
        """Check if a interface device exists"""
        cmd = [self.IP, "link", "show", "dev", self.name]
        return run(cmd, stdout=DEVNULL, stderr=DEVNULL).returncode == 0


class MacVlan(Interface):
    """Class to create macvlan interfaces Prefix assignment + interface creation"""

    def __init__(self, name: str, physical_int: str, *, mode: str = "bridge") -> None:
        self.name = name
        self.physical_interface = physical_int
        self.type = "macvlan"
        self.mode = mode

    def create(self) -> CompletedProcess:
        cmd = [
            self.IP,
            "link",
            "add",
            self.name,
            "link",
            self.physical_interface,
            "type",
            self.type,
            "mode",
            self.mode,
        ]
        LOG.info(
            f"Created {self.type} {self.name} bridged to {self.physical_interface}"
        )
        return run(cmd, check=True)


class Veth(Interface):
    """Veths pairs need to be made in default namespace then moved to NetNS"""

    def __init__(self, name: str, peer: str) -> None:
        self.name = name
        self.peer = peer
        self.type = "veth"

    def create(self) -> CompletedProcess:
        cmd = [self.IP, "link", "add", self.name, "type", self.type, "peer", self.peer]
        LOG.info(f"Created veth {self.name} with peer {self.peer}")
        return run(cmd, check=True)


def setup_all_veths(namespaces: Dict[str, Namespace]) -> None:
    """Setup all veths in a namespace then move to netns where needed"""
    for _ns_name, ns in namespaces.items():
        LOG.debug(f"Checking veths for {ns.name} namespace")
        for int_name, int_config in ns.interfaces.items():
            if int_config["type"] != "veth":
                continue

            if (
                ns.interface_exists(
                    int_name,
                    outside_ns=True,
                )
                == 0
                or (ns.ns_path.exists() and ns.interface_exists(int_name))
            ):
                LOG.debug(f"Not setting up {int_name} as it exists")
                continue

            veth = Veth(int_name, int_config["peer_name"])
            veth.create()
            LOG.info(f"Created {int_name} veth")


def setup_global_oob(
    interface_name: str, namespaces: Dict[str, Namespace], config: Dict
) -> None:
    """Add Global OOB interface if any netns has oob set to true"""
    oob_wanted = False
    for _, ns in namespaces.items():
        if ns.oob:
            oob_wanted = True
    if not oob_wanted:
        LOG.debug(
            "Not setting up a global OOB device. No namespace has an oob interface"
        )
        return

    oob_int = MacVlan(interface_name, config["physical_int"])
    oob_int.create()
