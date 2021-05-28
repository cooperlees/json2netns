import logging
from ipaddress import ip_interface
from subprocess import CompletedProcess, DEVNULL, PIPE, run
from typing import Any, Optional, Sequence, Union

from json2netns.consts import DEFAULT_IP, IPInterface


LOG = logging.getLogger(__name__)


def _run(ip: str, *args: Any, **kwargs: Any) -> CompletedProcess:
    """Subprocess run wrapper to allow for running within a netns
    - We only support CMD Sequence as the only non kwarg"""
    if "netns_name" in kwargs:
        if kwargs["netns_name"]:
            args = ([ip, "netns", "exec", kwargs["netns_name"]] + args[0],)
            LOG.debug(f"Running in {kwargs['netns_name']} netns: {' '.join(args[0])}")
        del kwargs["netns_name"]
    else:
        LOG.debug(f"Running: {' '.join(args[0])}")
    return run(*args, **kwargs)


class Interface:
    IP = DEFAULT_IP
    name = "Interface"
    type = "Interface"
    prefixes: Sequence[IPInterface] = ()

    def _convert_to_ip_interfaces(
        self, prefixes: Sequence[Union[IPInterface, str]]
    ) -> Sequence[IPInterface]:
        return [ip_interface(i) for i in prefixes]

    def add_prefixes(self, netns_name: str = "") -> None:
        for prefix in self.prefixes:
            cmd = [self.IP, "addr", "add", str(prefix), "dev", self.name]
            _run(
                self.IP,
                cmd,
                check=True,
                stdout=PIPE,
                stderr=PIPE,
                netns_name=netns_name,
            )
            log_msg = f"Added {prefix} to {self.name}"
            if netns_name:
                log_msg += f" in {netns_name} namespace"
            LOG.info(log_msg)

    def create(self) -> CompletedProcess:
        raise NotImplementedError("Each interface type needs to overload create")

    def delete(self, netns_name: str = "") -> Optional[CompletedProcess]:
        if not self.exists():
            LOG.debug(
                f"Not deleting {self.name} {self.type} interface as it does not exist ..."
            )
            return None

        cmd = [self.IP, "link", "del", self.name]
        LOG.info(f"Deleting {self.type} interface {self.name}")
        return _run(
            self.IP, cmd, check=True, stdout=PIPE, stderr=PIPE, netns_name=netns_name
        )

    def exists(self, netns_name: str = "") -> bool:
        """Check if a interface device exists"""
        cmd = [self.IP, "link", "show", "dev", self.name]
        return (
            _run(
                self.IP, cmd, stdout=DEVNULL, stderr=DEVNULL, netns_name=netns_name
            ).returncode
            == 0
        )

    def set_link_up(self, netns_name: str = "") -> bool:
        """Set the link to be administratively operational"""
        cmd = [self.IP, "link", "set", "up", "dev", self.name]
        return (
            _run(
                self.IP, cmd, stdout=DEVNULL, stderr=DEVNULL, netns_name=netns_name
            ).returncode
            == 0
        )

    def set_netns(self, netns_name: str) -> bool:
        """Set what namesapce the interface should be in"""
        cmd = [self.IP, "link", "set", self.name, "netns", netns_name]
        return run(cmd, stdout=DEVNULL, stderr=DEVNULL).returncode == 0


class Loopback(Interface):
    """Class to only support what we need for loopback interfaces"""

    name = "lo"
    type = "loopback"

    def __init__(self, prefixes: Sequence[str]) -> None:
        self.prefixes = self._convert_to_ip_interfaces(prefixes)

    def create(self) -> CompletedProcess:
        pass


class MacVlan(Interface):
    """Class to create macvlan interfaces Prefix assignment + interface creation"""

    def __init__(
        self,
        name: str,
        physical_int: str,
        prefixes: Sequence[Union[IPInterface, str]],
        *,
        mode: str = "bridge",
    ) -> None:
        self.name = name
        self.physical_interface = physical_int
        self.type = "macvlan"
        self.mode = mode
        self.prefixes = self._convert_to_ip_interfaces(prefixes)

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

    def __init__(
        self, name: str, peer: str, prefixes: Sequence[Union[IPInterface, str]]
    ) -> None:
        self.name = name
        self.peer = peer
        self.type = "veth"
        self.prefixes = self._convert_to_ip_interfaces(prefixes)

    def create(self) -> CompletedProcess:
        cmd = [self.IP, "link", "add", self.name, "type", self.type, "peer", self.peer]
        LOG.info(f"Created veth {self.name} with peer {self.peer}")
        return run(cmd, check=True)
