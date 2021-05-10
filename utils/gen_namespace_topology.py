#!/usr/bin/env python3

import argparse
import logging
import sys
from json import load
from pathlib import Path


LOG = logging.getLogger(__name__)
PROJECT_DIR = Path(__file__).parent.parent.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Verbose debug output"
    )
    parser.add_argument("config", help="Path to save JSON topology config")
    parser.add_argument("ns_count", help="Number of namespaces to put in config")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        level=log_level,
    )
    LOG.debug(f"Starting {sys.argv[0]} ...")

    base_config = PROJECT_DIR / "sameple_configs" / "base.json"
    with base_config.open("rb") as bcfp:
        config = load(bcfp)
    
    for idx in range(1, int(ns_count)):
        print(f"NS Count {ns_count}")

    return 0


if __name__ == "__main__":  # pragma: nocover
    sys.exit(main())
