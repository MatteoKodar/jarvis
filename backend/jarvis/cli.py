import argparse
import getpass
import sqlite3
from pathlib import Path
from .db import initialize, connect
from .auth import set_owner

def main():
    parser = argparse.ArgumentParser(description="JARVIS lokal administration")
    parser.add_argument("command", choices=["owner", "backup"])
    parser.add_argument("--output", default="jarvis-backup.sqlite3")
    args = parser.parse_args()
    initialize()
    if args.command == "owner":
        password = getpass.getpass("Välj ägarlösenord (minst 12 tecken): ")
        if password != getpass.getpass("Upprepa lösenordet: "):
            raise SystemExit("Lösenorden matchar inte.")
        set_owner(password)
        print("Ägarkontot är sparat. Inga standardlösenord används.")
    else:
        output = Path(args.output).resolve()
        if output.exists():
            raise SystemExit("Målfilen finns redan. Välj ett nytt filnamn.")
        with connect() as source, sqlite3.connect(output) as target:
            source.backup(target)
        print("Säkerhetskopia skapad:", output)

if __name__ == "__main__":
    main()
