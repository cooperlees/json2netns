import logging
from subprocess import CompletedProcess, DEVNULL, PIPE, run
from typing import Optional, Sequence

from json2netns.consts import DEFAULT_IP, IPInterface


LOG = logging.getLogger(__name__)


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

    def set_link_up(self) -> bool:
        """Check if a interface device exists"""
        cmd = [self.IP, "link", "set", "up", "dev", self.name]
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
