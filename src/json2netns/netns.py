import asyncio
import logging
from pathlib import Path
from subprocess import run


IP = "/usr/sbin/ip"
LOG = logging.getLogger(__name__)


class Namespace:
    def __init__(self, name: str) -> None:
        self.name = name

    def create(self, delete: bool = False) -> None:
        ns_path = Path(f"/run/netns/{self.name}")
        if not delete and not ns_path.exists():
            LOG.info(f"Namespace {self.name} already exists ...")
            return None
        elif delete and ns_path.exists():
            LOG.info(f"Namespace {self.name} does not exist ...")
            return None

        op = "del" if delete else "add"
        run(*[f"{IP}", "netns", op, self.ns_name], check=True)
        LOG.info(f"Successfully '{op}'ed {self.name} namespace")

    def delete(self) -> None:
        self.create(delete=True)