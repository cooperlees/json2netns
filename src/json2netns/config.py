import logging
from json import load
from pathlib import Path
from typing import Dict


LOG = logging.getLogger(__name__)


class Config:
    """Handle the JSON config file"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Dict:
        """Load JSON config to use with creating Namespace objects"""
        with self.path.open("rb") as cfp:
            return dict(load(cfp))

    # TODO: Validate config
    def validate(self, config: Dict) -> None:
        """High level config validator"""
        pass
