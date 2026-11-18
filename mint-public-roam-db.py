#!/usr/bin/env python3
"""Mint a PUBLIC org-roam.db from org files in this directory only.

Emacs does not visit this tree. org-roam-ui's GitHub Action consumes the db;
it does not build one. Run this script after adding/changing public org files,
then commit org-roam.db.

Does not read /srv/org/roam.db. Private operating copies stay in-house.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "org-roam.db"
ID_RE = re.compile(r":ID:\s*(\S+)", re.I)
TITLE_RE = re.compile(r"^#\+TITLE:\s*(.+)$", re.I | re.M)
LINK_RE = re.compile(r"\[\[id:([^]]+)\]\[")


def emacs_time(ts: float) -> str:
    # org-roam stores Emacs high-precision time lists
    t = int(ts)
    high, low = divmod(t, 65536)
    return f"({high} {low} 0 0)"


def quoted(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_org(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    mid = ID_RE.search(text)
    if not mid:
        raise SystemExit(f"no :ID: in {path.name}")
    title_m = TITLE_RE.search(text)
    title = title_m.group(1).strip() if title_m else path.stem
    dests = LINK_RE.findall(text)
    sha = hashlib.sha1(text.encode("utf-8")).hexdigest()
    st = path.stat()
    return {
        "id": mid.group(1),
        "title": title,
        "file": str(path),
        "hash": sha,
        "atime": emacs_time(st.st_atime),
        "mtime": emacs_time(st.st_mtime),
        "links": dests,
        "text": text,
    }


def main() -> None:
    files = sorted(ROOT.glob("*.org"))
    if not files:
        raise SystemExit("no public .org files")
    parsed = [parse_org(p) for p in files]
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE files (
          file UNIQUE PRIMARY KEY, title, hash NOT NULL,
          atime NOT NULL, mtime NOT NULL
        );
        CREATE TABLE nodes (
          id NOT NULL PRIMARY KEY, file NOT NULL, level NOT NULL, pos NOT NULL,
          todo, priority, scheduled text, deadline text, title, properties, olp,
          FOREIGN KEY (file) REFERENCES files (file) ON DELETE CASCADE
        );
        CREATE TABLE aliases (
          node_id NOT NULL, alias,
          FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
        );
        CREATE TABLE citations (
          node_id NOT NULL, cite_key NOT NULL, pos NOT NULL, properties,
          FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
        );
        CREATE TABLE refs (
          node_id NOT NULL, ref NOT NULL, type NOT NULL,
          FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
        );
        CREATE TABLE tags (
          node_id NOT NULL, tag,
          FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE
        );
        CREATE TABLE links (
          pos NOT NULL, source NOT NULL, dest NOT NULL, type NOT NULL, properties NOT NULL,
          FOREIGN KEY (source) REFERENCES nodes (id) ON DELETE CASCADE
        );
        """
    )
    ids = {p["id"] for p in parsed}
    pos = 1
    for p in parsed:
        c.execute(
            "INSERT INTO files(file, title, hash, atime, mtime) VALUES (?,?,?,?,?)",
            (quoted(p["file"]), quoted(p["title"]), quoted(p["hash"]), p["atime"], p["mtime"]),
        )
        props = f'(("FILE" . {quoted(p["file"])}) ("ID" . {quoted(p["id"])}))'
        c.execute(
            """INSERT INTO nodes(id, file, level, pos, title, properties, olp)
               VALUES (?,?,?,?,?,?,?)""",
            (quoted(p["id"]), quoted(p["file"]), 0, 1, quoted(p["title"]), props, "nil"),
        )
        for dest in p["links"]:
            if dest not in ids:
                print(f"skip dangling id link {p['id']} -> {dest}")
                continue
            c.execute(
                "INSERT INTO links(pos, source, dest, type, properties) VALUES (?,?,?,?,?)",
                (pos, quoted(p["id"]), quoted(dest), quoted("id"), "nil"),
            )
            pos += 1
    conn.commit()
    conn.close()
    print(f"minted {DB} from {len(parsed)} public org files")


if __name__ == "__main__":
    main()
