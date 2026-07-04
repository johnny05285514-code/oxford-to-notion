import argparse
import sys
from collections.abc import Sequence
from typing import Any

from notion_client import Client

from config import Settings
from exceptions import AppError
from notion_writer import NotionWriter
from oxford_client import OxfordClient, normalize_word


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import an Oxford Learner's Dictionaries entry into Notion."
    )
    parser.add_argument("word", help="one English word, for example: brutality")
    return parser


def build_dependencies() -> tuple[OxfordClient, NotionWriter]:
    settings = Settings.from_env()
    notion_client = Client(auth=settings.notion_token)
    return OxfordClient(), NotionWriter(notion_client, settings.notion_database_id)


def run(
    argv: Sequence[str] | None = None,
    *,
    oxford: Any | None = None,
    notion: Any | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        word = normalize_word(args.word)
        if oxford is None or notion is None:
            oxford, notion = build_dependencies()
        entry = oxford.lookup(word)
        page_url = notion.upsert(entry)
    except (AppError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1 if isinstance(exc, AppError) else 2
    except Exception:
        print("Error: Unexpected failure while importing the word.", file=sys.stderr)
        return 1

    print(f"Imported '{entry.word}': {page_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
