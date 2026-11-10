import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from .client import (
    lookup_business_postal_code,
    lookup_postal_code,
    refresh_cache,
    search_postal_codes,
)


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="jp-postal-code-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("lookup-postal-code", argument_default=SUPPRESS)
    command.add_argument("--postal-code", required=True)
    command.set_defaults(handler=lookup_postal_code)

    command = commands.add_parser("search-postal-codes", argument_default=SUPPRESS)
    command.add_argument("--address", required=True)
    command.add_argument("--prefecture")
    command.add_argument("--limit", type=int)
    command.add_argument("--offset", type=int)
    command.set_defaults(handler=search_postal_codes)

    command = commands.add_parser("lookup-business-postal-code", argument_default=SUPPRESS)
    command.add_argument("--postal-code", required=True)
    command.set_defaults(handler=lookup_business_postal_code)

    command = commands.add_parser("refresh", argument_default=SUPPRESS)
    command.add_argument("--dataset", choices=["address", "business"])
    command.set_defaults(handler=refresh_cache)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
