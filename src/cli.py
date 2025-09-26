"""Minimal CLI entrypoints for the project."""

import argparse

from .etl import run_pipeline
from .model import train_and_persist


def main() -> None:
    parser = argparse.ArgumentParser(description="Museum attendance tooling")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("etl", help="Run ingestion and city population updates.")
    train_parser = subparsers.add_parser("train", help="Train regression model.")
    train_parser.add_argument(
        "--min-visitors",
        type=int,
        default=500_000,
        help="Minimum visitors threshold for training rows (default 500k).",
    )

    args = parser.parse_args()

    if args.command == "etl":
        run_pipeline(save_raw=False)
    elif args.command == "train":
        train_and_persist(min_visitors=args.min_visitors)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

