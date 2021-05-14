#!/usr/bin/env python3

import argparse
import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from getpass import getuser
from pathlib import Path
from typing import Awaitable, Dict, List
from json2netns.config import Config
from json2netns.netns import Namespace, MacVlan, setup_all_veths, setup_global_oob

GLOBAL_OOB_INTERFACE = "oob0"
LOG = logging.getLogger(__name__)
VALID_ACTIONS = {"create", "delete", "check"}
VALID_SORTED_ACTIONS = sorted(VALID_ACTIONS)


def amiroot() -> bool:
    return getuser() == "root"


async def async_main(args: argparse.Namespace) -> int:
    config = Config(Path(args.config))
    topology_config = config.load()
    executor = ThreadPoolExecutor(max_workers=args.workers)

    namespaces: Dict[str, Namespace] = {}
    for ns_name, ns_config in topology_config["namespaces"].items():
        namespaces[ns_name] = Namespace(ns_name, ns_config, topology_config)

    if not amiroot():
        LOG.error("Please `sudo` / become root to run netns commands")
        return 69

    lower_action = args.action.lower()
    if lower_action == "check":
        ns_count = 0
        for ns_name, ns in namespaces.items():
            if ns_count != 0:
                print("")
            print(f"# Checking {ns_name}")
            ns.check()
            ns_count += 1

        LOG.debug(f"Ran check commands for {ns_count} NSs")
        return 0

    # Perform non co-ro fun
    if lower_action == "create":
        # veth pairs need to be setup then moved to namespaces
        setup_all_veths(namespaces)
        # Add global oob if wanted
        setup_global_oob(GLOBAL_OOB_INTERFACE, namespaces, topology_config)
    elif lower_action == "delete":
        # Check if we have an oob device and clean it up
        oob_int = MacVlan(GLOBAL_OOB_INTERFACE, "deleting_only")
        oob_int.delete()

    # Create NS Coros and run in parallel
    loop = asyncio.get_running_loop()
    namespace_coros: List[Awaitable] = []
    for _ns_name, ns in namespaces.items():
        if lower_action == "create":
            namespace_coros.append(loop.run_in_executor(executor, ns.setup))
        elif lower_action == "delete":
            namespace_coros.append(loop.run_in_executor(executor, ns.delete))

    if not namespace_coros:
        LOG.error(f"Nothing to do. Is {lower_action} a valid action?")
        return 10

    try:
        await asyncio.gather(*namespace_coros)
    except Exception as e:
        LOG.error(f"{sys.argv[0]} Failed: {e}")
        return -1
    return 0


def validate_args(args: argparse.Namespace) -> int:
    """Look at args and make sure that are valid"""
    config_path = Path(args.config)
    if not config_path.exists():
        LOG.error("We need a JSON topology config to do anything")
        return 1

    if args.action.lower() not in VALID_ACTIONS:
        LOG.error(
            f"{args.action} is not a valid action choice! Valid choices: "
            + f"'{' '.join(VALID_SORTED_ACTIONS)}'"
        )
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Verbose debug output"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate JSON config (not yet implemented)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of threads to for per netns operations",
    )
    parser.add_argument("config", help="Path to JSON topology config")
    parser.add_argument(
        "action", help=f"Action to perform: {'|'.join(VALID_SORTED_ACTIONS)}"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        level=log_level,
    )
    LOG.debug(f"Starting {sys.argv[0]} ...")
    error_value = validate_args(args)
    if error_value:
        return error_value
    return int(asyncio.run(async_main(args)))


if __name__ == "__main__":  # pragma: nocover
    sys.exit(main())
