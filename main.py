import argparse
import sys
from collections.abc import Sequence
from typing import Any

from exceptions import AppError
from import_service import build_dependencies, import_word


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import an Oxford Learner's Dictionaries entry into Notion."
    )
    parser.add_argument("word", help="one English word, for example: brutality")
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    oxford: Any | None = None,
    notion: Any | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = import_word(
            args.word,
            oxford=oxford,
            notion=notion,
            dependency_factory=build_dependencies,
        )
    except (AppError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1 if isinstance(exc, AppError) else 2
    except Exception:
        print("Error: Unexpected failure while importing the word.", file=sys.stderr)
        return 1

    print(f"Imported '{result.word}': {result.page_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
