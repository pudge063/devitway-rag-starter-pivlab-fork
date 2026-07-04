import sys
import typing
from dotenv import load_dotenv
import click

from .ingest import main as ingest_main
from .mcp_server import get_mcp

CallableCliOption = typing.TypeVar("CallableCliOption", bound=typing.Callable)  # type: ignore

INGEST_OPTIONS: dict[str, typing.Any] = {
    "verbose": click.option(
        "--verbose",
        "-v",
        help="verbose",
        type=bool,
        default=False,
    ),
    "docs_dir": click.option(
        "--docs-dir",
        "-d",
        help="docs dir",
        type=str,
        default="./docs",
    ),
}

MCP_SERVER_OPTIONS: dict[str, typing.Any] = {}


@click.group()
def cli() -> None:
    """RAG management tool"""


def ingest_options(fn: CallableCliOption) -> CallableCliOption:
    for option in INGEST_OPTIONS.keys():
        fn = INGEST_OPTIONS[option](fn)
    return fn


def mcp_server_options(fn: CallableCliOption) -> CallableCliOption:
    for option in MCP_SERVER_OPTIONS.keys():
        fn = MCP_SERVER_OPTIONS[option](fn)
    return fn


@cli.command(
    "ingest",
    help="docs inguest",
)
@ingest_options
def ingest(
    *,
    docs_dir: str,
    **_,
):
    load_dotenv()
    ingest_main(docs_dir=docs_dir)


@cli.command(
    "mcp-server",
    help="run mcp server",
)
@mcp_server_options
def mcp_server():
    mcp = get_mcp()
    mcp.run()


if __name__ == "__main__":
    sys.exit(cli())
