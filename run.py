#!/usr/bin/env python3
"""Start the NeuroFlow Connect MVP."""

from __future__ import annotations

import argparse

from neuroflow.app import DEFAULT_DB, serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NeuroFlow Connect synthetic-data MVP")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    args = parser.parse_args()
    serve(args.host, args.port, args.db)


if __name__ == "__main__":
    main()

