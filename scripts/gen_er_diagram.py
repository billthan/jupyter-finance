#!/usr/bin/env python3
"""Generate the database ER diagram (Mermaid) from db/postgres/init.sql and
inject it into nbs/docs_database.ipynb.

Run before `nbdev_docs` so the published diagram always matches the schema.
This replaces the previously hand-maintained Mermaid block, which had already
drifted from init.sql.

Usage:
    python scripts/gen_er_diagram.py            # write into the notebook
    python scripts/gen_er_diagram.py --check    # fail if notebook is out of date
    python scripts/gen_er_diagram.py --print     # print diagram to stdout
"""
from __future__ import annotations
import json, re, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_SQL = ROOT / "db" / "postgres" / "init.sql"
NOTEBOOK = ROOT / "nbs" / "docs_database.ipynb"

# Reserved words that begin a table-level constraint rather than a column.
_CONSTRAINT_STARTS = ("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK")


def _split_columns(body: str) -> list[str]:
    """Split a CREATE TABLE body into top-level definition strings, respecting
    parentheses (so NUMERIC(10, 2) is not split on its comma)."""
    parts, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def _mermaid_type(sql_type: str) -> str:
    """Normalize a SQL type to a compact token for the diagram."""
    t = sql_type.lower()
    if t.startswith("varchar") or t.startswith("character varying"):
        return "varchar"
    if t.startswith("numeric") or t.startswith("decimal"):
        return "numeric"
    if t in ("serial", "bigserial"):
        return "int"
    if t.startswith("int") or t == "integer" or t == "bigint":
        return "int"
    if t.startswith("timestamp"):
        return "timestamp"
    # float, date, boolean, text, bytea, etc. pass through as the first word
    return t.split("(")[0]


def parse_schema(sql: str):
    """Return (tables, relationships).

    tables: list of (name, [(col, type, key_marker, comment), ...]) preserving
            declaration order.
    relationships: list of (parent, child) from FOREIGN KEY constraints.
    """
    tables, relationships = [], []
    # Match each CREATE TABLE ... ( ... );  (non-greedy, DOTALL)
    for m in re.finditer(r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\n\s*\)\s*;", sql, re.S | re.I):
        name = m.group(1).upper()
        # Strip SQL line comments so "-- e.g. 'plaid'" is not parsed as a column.
        body = re.sub(r"--[^\n]*", "", m.group(2))
        pk_cols, fk_cols = set(), {}

        # First pass: collect PK (inline + table-level) and FK targets.
        for raw in _split_columns(body):
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("PRIMARY KEY"):
                for c in re.findall(r"\((.*?)\)", line):
                    pk_cols.update(x.strip().lower() for x in c.split(","))
            elif upper.startswith("CONSTRAINT") or upper.startswith("FOREIGN KEY"):
                fkm = re.search(r"FOREIGN\s+KEY\s*\((\w+)\)\s*REFERENCES\s+(\w+)", line, re.I)
                if fkm:
                    fk_cols[fkm.group(1).lower()] = fkm.group(2).upper()
                    relationships.append((fkm.group(2).upper(), name))
            elif "PRIMARY KEY" in upper and not upper.startswith(_CONSTRAINT_STARTS):
                pk_cols.add(line.split()[0].lower())

        # Second pass: emit columns in declaration order.
        cols = []
        for raw in _split_columns(body):
            line = raw.strip()
            if not line or line.upper().startswith(_CONSTRAINT_STARTS):
                continue
            tokens = line.split()
            if len(tokens) < 2:
                continue
            col = tokens[0].lower()
            col_type = _mermaid_type(tokens[1])
            marker = "PK" if col in pk_cols else ("FK" if col in fk_cols else "")
            # Preserve an inline comment for special columns (e.g. encrypted token).
            comment = ""
            if col == "plaid_access_token":
                comment = "Encrypted"
            cols.append((col, col_type, marker, comment))

        tables.append((name, cols))
    return tables, relationships


def render_mermaid(tables, relationships) -> str:
    lines = ["erDiagram"]
    for name, cols in tables:
        lines.append(f"    {name} {{")
        for col, col_type, marker, comment in cols:
            row = f"        {col_type} {col}"
            if marker:
                row += f" {marker}"
            if comment:
                row += f' "{comment}"'
            lines.append(row)
        lines.append("    }")
        lines.append("")
    lines.append("    %% Relationships (generated from FOREIGN KEY constraints)")
    for parent, child in relationships:
        lines.append(f'    {parent} ||--o{{ {child} : "has many"')
    return "\n".join(lines)


def build_cell_source(diagram: str) -> str:
    return (
        "<!-- AUTO-GENERATED from db/postgres/init.sql by "
        "scripts/gen_er_diagram.py. Do not edit by hand. -->\n"
        "```{mermaid}\n" + diagram + "\n```"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if notebook is stale")
    ap.add_argument("--print", action="store_true", dest="do_print")
    args = ap.parse_args()

    sql = INIT_SQL.read_text()
    tables, rels = parse_schema(sql)
    diagram = render_mermaid(tables, rels)
    new_source = build_cell_source(diagram)

    if args.do_print:
        print(diagram)
        return

    nb = json.loads(NOTEBOOK.read_text())
    # Find the markdown cell that holds the mermaid block.
    target = None
    for c in nb["cells"]:
        if c["cell_type"] == "markdown" and "```{mermaid}" in "".join(c["source"]):
            target = c
            break
    if target is None:
        print("ERROR: no mermaid cell found in docs_database.ipynb", file=sys.stderr)
        sys.exit(2)

    current = "".join(target["source"])
    if args.check:
        if current.strip() != new_source.strip():
            print("docs_database.ipynb ER diagram is OUT OF DATE. "
                  "Run: python scripts/gen_er_diagram.py", file=sys.stderr)
            sys.exit(1)
        print("ER diagram is up to date.")
        return

    target["source"] = new_source.splitlines(keepends=True)
    NOTEBOOK.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"Updated {NOTEBOOK.relative_to(ROOT)} with {len(tables)} tables, "
          f"{len(rels)} relationships.")


if __name__ == "__main__":
    main()
