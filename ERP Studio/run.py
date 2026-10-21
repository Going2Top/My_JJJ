"""Run with: python run.py (Python 3.10+, no pip installation required)."""
import argparse
import logging

from erp_demo.server import serve


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local ERP Studio demonstration")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--database", help="Optional SQLite database path")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    serve(args.host, args.port, args.database)
