import logging
from ipaddress import ip_interface, ip_network
from pathlib import Path
from subprocess import CompletedProcess, DEVNULL, run
from typing import Dict, List, Optional, Sequence

from json2netns.consts import DEFAULT_IP, IPInterface
from json2netns.interfaces import Interface, Loopback, MacVlan, Veth


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
        self.interfaces = self._create_interface_objects()
        self.routes = ns_config["routes"]

        self.oob = ns_config["oob"]
        self.oob_prefixes = None
        if self.oob:
            self.oob_prefixes = [
                ip_network(prefix) for prefix in config["oob"]["prefixes"]
            ]

    def _create_interface_objects(self) -> Dict[str, Interface]:
        """Read namespace interfaces out of config and create Interface objects"""
        interfaces: Dict[str, Interface] = {}
        for name, int_conf in self.config["namespaces"][self.name][
            "interfaces"
        ].items():
            if int_conf["type"].lower() in {"lo", "loopback"}:
                interfaces["lo"] = Loopback(int_conf["prefixes"])
            elif int_conf["type"].lower() == "macvlan":
                interfaces[name] = MacVlan(
                    name, self.config["physical_int"], int_conf["prefixes"]
                )
            elif int_conf["type"].lower() == "veth":
                interfaces[name] = Veth(
                    name, int_conf["peer_name"], int_conf["prefixes"]
                )
            else:
                raise ValueError(
                    f"{int_conf['type']} is not supported yet ... PR time?"
                )

        # We always want loopback up so add with no prefixes if non are supplied
        if "lo" not in interfaces:
            interfaces["lo"] = Loopback(())

        return interfaces

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

        op = "Delete" if delete else "Add"
        d = "d" if delete else "ed"
        cp = run((f"{self.IP}", "netns", op.lower(), self.name), check=check)
        LOG.info(f"{op}{d} {self.name} namespace")
        return cp

    def check(self) -> None:
        for header, cmd in self.check_commands.items():
            print(header, flush=True)
            self.exec_in_ns(cmd, check=False)

    def create(self, delete: bool = False) -> None:
        self._create_or_delete(delete=False)

    def delete(self) -> None:
        self._create_or_delete(delete=True)

    def create_oob(self) -> None:
        """If configured, add a OOB device to connect to global namespace
        + bridge with a physical interface"""
        if not self.oob:
            LOG.debug(f"No oob configred for {self.name}")
            return

        physical_int = (
            self.config["physical_int"] if "physical_int" in self.config else ""
        )
        if not physical_int:
            raise ValueError(
                f"No Physical int to bridge macvlan OOB interface with for {self.name}"
            )
        oob_prefixes = self.oob_addrs()
        oob_int = MacVlan(f"oob{self.id}", physical_int, oob_prefixes)
        oob_int.create()
        oob_int.set_netns(self.name)
        oob_int.add_prefixes(self.name)
        oob_int.set_link_up(self.name)

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

    # TODO: Add route support
    def route_add(self) -> None:
        """Add any needed static routes in netns"""
        pass

    def setup_links(self) -> None:
        """Create virtual network device and assign to the netns"""
        for _int_name, int_obj in self.interfaces.items():
            if not int_obj.exists():
                int_obj.create()

            int_obj.set_netns(self.name)
            int_obj.add_prefixes(self.name)
            int_obj.set_link_up(self.name)

    def setup(self) -> None:
        """Coordination function to setup all the namespace elements
        - Designed to be idempotent - i.e. if it exists, move on"""
        # Create netns
        self.create()
        # Create links/interfaces + address them + assign to netns
        self.setup_links()
        # Create oob if selected
        self.create_oob()
        # Add any static routes
        self.route_add()

        LOG.info(f"Finished setup of {self.name} namespace")


def setup_all_veths(namespaces: Dict[str, "Namespace"]) -> int:
    """Setup all veths in a namespace then move to netns where needed"""
    errors = 0
    for _ns_name, ns in namespaces.items():
        LOG.debug(f"Setting up veths for {ns.name} namespace")
        for int_name, int_obj in ns.interfaces.items():
            if int_obj.exists():
                LOG.debug(f"{int_name} exists. Not creating")
                continue

            if not int_obj.create() and int_name != "lo":
                LOG.error(f"FAILED to create {int_name}")
                errors += 1

    return errors


def setup_global_oob(
    interface_name: str, namespaces: Dict[str, "Namespace"], config: Dict
) -> None:
    """Add Global OOB interface if any netns has oob set to true"""
    oob_wanted = False
    for _, ns in namespaces.items():
        if ns.oob:
            oob_wanted = True
            break

    if not oob_wanted:
        LOG.debug(
            "Not setting up a global OOB device. No namespace has an oob interface"
        )
        return None

    oob_int_prefixes = []
    if "oob" in config and "prefixes" in config["oob"]:
        oob_int_prefixes = [ip_interface(ip) for ip in config["oob"]["prefixes"]]

    oob_int = MacVlan(interface_name, config["physical_int"], oob_int_prefixes)
    oob_int.create()
    oob_int.add_prefixes()
    oob_int.set_link_up()
