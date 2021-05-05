#!/usr/bin/env python3

import argparse
import asyncio
import logging
import sys


LOG = logging.getLogger(__name__)


async def async_main(args: argparse.Namespace) -> int:
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Verbose debug output"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        level=log_level,
    )
    LOG.debug(f"Starting {sys.argv[0]} ...")
    return asyncio.run(async_main(args))


if __name__ == "__main__":  # pragma: nocover
    sys.exit(main())
