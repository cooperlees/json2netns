#!/usr/bin/env python3

import argparse
import logging
import sys
from copy import deepcopy
from json import dumps, load
from pathlib import Path


LOG = logging.getLogger(__name__)
PROJECT_DIR = Path(__file__).parent.parent.resolve()


def main() -> int:
    """Generic join namespaces on a stick"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Verbose debug output"
    )
    parser.add_argument("config", help="Path to save JSON topology config")
    parser.add_argument(
        "ns_count", type=int, default=1, help="Number of namespaces to put in config"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        level=log_level,
    )
    LOG.debug(f"Starting {sys.argv[0]} ...")

    base_config = PROJECT_DIR / "sample_configs" / "base.json"
    with base_config.open("rb") as bcfp:
        config = load(bcfp)
    ns_base_config = deepcopy(config["namespaces"]["example_namespace"])
    LOG.debug("Deleting default example_namesapce")
    del config["namespaces"]["example_namespace"]

    ns_count = args.ns_count + 1
    for idx in range(1, int(ns_count)):
        LOG.info(f"-> Making Namespace {idx}")
        ns_conf = deepcopy(ns_base_config)
        ns_name = f"ns{idx}"
        ns_conf["id"] = idx

        # TODO: Fix interfaces + automate addressing

        config["namespaces"][ns_name] = ns_conf

    print(dumps(config, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: nocover
    sys.exit(main())
