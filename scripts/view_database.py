"""Generate a single self-contained HTML snapshot of the Agricure database.

No app to install: this reads the SQLite demo database (or PostgreSQL if
DATABASE_URL points at one) and writes `database_view.html` in the project root,
then opens it in your default browser. Sample images stored in backend/uploads
are shown inline.

Run:
    backend/.venv/Scripts/python scripts/view_database.py
    backend/.venv/Scripts/python scripts/view_database.py --no-open
    backend/.venv/Scripts/python scripts/view_database.py --limit 500
"""
import argparse
import html
import json
import os
import sqlite3
import sys
import webbrowser
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

OUT = os.path.join(ROOT, "database_view.html")

# Columns whose values are file paths to show as thumbnails
IMAGE_COLUMNS = ("image_path", "image_url")
# Columns holding JSON that is nicer pretty-printed
JSON_COLUMNS = ("risk_factors", "factors", "metadata_json")

PRIORITY_TABLES = [
    "users", "farms", "crop_reports", "agent_decisions", "agent_activity",
    "recommendations", "officer_verifications", "referrals", "sensor_readings",
    "notifications", "model_feedback", "model_versions", "audit_logs",
]


def find_sqlite_db() -> str | None:
    """Locate the SQLite file the backend actually uses."""
    candidates = [
        os.path.join(ROOT, "backend", "agricure_dev.db"),  # normal (cwd=backend)
        os.path.join(ROOT, "agricure_dev.db"),             # stray root copy
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Fall back to whatever DATABASE_URL says, when it is a sqlite path
    try:
        from app.config import settings

        url = settings.DATABASE_URL
        if url.startswith("sqlite"):
            rel = url.split("///")[-1]
            if os.path.isabs(rel) and os.path.exists(rel):
                return rel
            for base in (os.path.join(ROOT, "backend"), ROOT):
                p = os.path.join(base, rel.lstrip("./"))
                if os.path.exists(p):
                    return p
    except Exception:
        pass
    return None


def connect_postgres():
    """Return a SQLAlchemy connection for PostgreSQL, or None."""
    try:
        from app.config import settings
        from sqlalchemy import create_engine

        if not settings.DATABASE_URL.startswith("postgresql"):
            return None
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        return engine.connect()
    except Exception as exc:
        print(f"  (PostgreSQL not reachable: {str(exc)[:80]})")
        return None


def list_tables_sqlite(conn) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [r[0] for r in rows]


def list_tables_pg(conn) -> list[str]:
    from sqlalchemy import text

    rows = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )).fetchall()
    return [r[0] for r in rows]


def fetch(conn, table: str, limit: int, is_sqlite: bool):
    if is_sqlite:
        cur = conn.execute(f'SELECT * FROM "{table}" LIMIT {limit}')
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchall()
    from sqlalchemy import text

    res = conn.execute(text(f'SELECT * FROM "{table}" LIMIT {limit}'))
    return list(res.keys()), res.fetchall()


def count_rows(conn, table: str, is_sqlite: bool) -> int:
    if is_sqlite:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    from sqlalchemy import text

    return conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0


def render_cell(col: str, value, project_root: str) -> str:
    if value is None:
        return '<span class="null">—</span>'

    # Thumbnails for stored sample images
    if col in IMAGE_COLUMNS and isinstance(value, str) and value:
        rel = value
        if os.path.isabs(rel):
            try:
                rel = os.path.relpath(rel, project_root)
            except ValueError:
                rel = value
        elif not rel.startswith(("http://", "https://", "backend/")):
            rel = os.path.join("backend", rel.lstrip("./\\"))
        rel = rel.replace("\\", "/")
        if rel.startswith(("http://", "https://")):
            return f'<a href="{html.escape(value)}" target="_blank">{html.escape(value)}</a>'
        return (
            f'<a href="{html.escape(rel)}" target="_blank">'
            f'<img class="thumb" src="{html.escape(rel)}" alt="sample" '
            f'onerror="this.replaceWith(document.createTextNode(\'file missing\'))"></a>'
        )

    text = str(value)
    if col in JSON_COLUMNS:
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, indent=None, ensure_ascii=False)
        except Exception:
            pass
    if len(text) > 160:
        text = text[:160] + "…"
    return html.escape(text)


def build_html(db_label: str, tables: dict, total_rows: int, limit: int) -> str:
    generated = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    nav = "\n".join(
        f'<a href="#{t}">{html.escape(t)} <span class="badge">{len(rows)}</span></a>'
        for t, (cols, rows, total) in tables.items()
    )

    sections = []
    for table, (cols, rows, total) in tables.items():
        if not cols:
            sections.append(
                f'<section id="{table}"><h2>{html.escape(table)}</h2>'
                f'<p class="empty">No data.</p></section>'
            )
            continue
        head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
        body = "\n".join(
            "<tr>" + "".join(f"<td>{render_cell(c, v, ROOT)}</td>" for c, v in zip(cols, row)) + "</tr>"
            for row in rows
        )
        note = ""
        if total > len(rows):
            note = f'<p class="note">Showing the first {len(rows)} of {total} rows (use --limit to see more).</p>'
        sections.append(
            f'<section id="{table}"><h2>{html.escape(table)} '
            f'<span class="count">{total} rows</span></h2>{note}'
            f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
            f'</section>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Agricure database snapshot</title>
<style>
  :root {{ --forest:#1f3d2b; --forest-dark:#132920; --moss:#4f7942; --wheat:#d8a53d;
           --cream:#faf6ec; --cream-deep:#f1ead8; --ink:#14231a; --line:rgba(20,35,26,.12); }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Inter",-apple-system,Segoe UI,Roboto,sans-serif; color:var(--ink);
         background:var(--cream); display:flex; min-height:100vh; }}
  aside {{ width:250px; flex-shrink:0; background:var(--forest-dark); color:#fff; padding:22px 16px;
           position:sticky; top:0; height:100vh; overflow-y:auto; }}
  aside h1 {{ font-family:Georgia,serif; font-size:19px; margin:0 0 4px; font-weight:400; }}
  aside p {{ font-size:11px; color:rgba(255,255,255,.6); margin:0 0 18px; word-break:break-all; }}
  aside a {{ display:flex; justify-content:space-between; gap:8px; align-items:center; color:rgba(255,255,255,.85);
             text-decoration:none; font-size:13px; padding:7px 10px; border-radius:8px; }}
  aside a:hover {{ background:rgba(255,255,255,.1); color:#fff; }}
  .badge {{ background:var(--wheat); color:var(--forest-dark); font-size:10px; font-weight:700;
            padding:1px 7px; border-radius:999px; }}
  main {{ flex:1; padding:26px 30px 60px; min-width:0; }}
  header.top {{ border-bottom:1px solid var(--line); padding-bottom:16px; margin-bottom:22px; }}
  header.top h1 {{ font-family:Georgia,serif; font-weight:400; margin:0 0 6px; color:var(--forest); }}
  header.top p {{ margin:4px 0 0; font-size:13px; color:rgba(20,35,26,.6); }}
  .stats {{ display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }}
  .stat {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:8px 14px; font-size:12px; }}
  .stat b {{ display:block; font-size:20px; font-family:Georgia,serif; color:var(--forest); }}
  section {{ margin-bottom:34px; scroll-margin-top:16px; }}
  section h2 {{ font-family:Georgia,serif; font-weight:400; font-size:20px; color:var(--forest);
                margin:0 0 8px; display:flex; align-items:center; gap:10px; }}
  .count {{ font-family:inherit; font-size:11px; background:var(--cream-deep); color:var(--moss);
            border-radius:999px; padding:2px 9px; font-weight:600; }}
  .scroll {{ overflow-x:auto; background:#fff; border:1px solid var(--line); border-radius:10px; }}
  table {{ border-collapse:collapse; font-size:12px; width:100%; }}
  th, td {{ text-align:left; padding:7px 11px; border-bottom:1px solid var(--line); vertical-align:top;
            white-space:nowrap; }}
  th {{ background:var(--cream-deep); position:sticky; top:0; font-weight:600; font-size:11px;
        text-transform:uppercase; letter-spacing:.04em; color:rgba(20,35,26,.6); }}
  tbody tr:hover {{ background:rgba(79,121,66,.06); }}
  .null {{ color:rgba(20,35,26,.3); }}
  .thumb {{ width:52px; height:52px; object-fit:cover; border-radius:7px; border:1px solid var(--line);
            display:block; }}
  .note, .empty {{ font-size:12px; color:rgba(20,35,26,.55); margin:0 0 8px; }}
  a {{ color:var(--moss); }}
</style>
</head>
<body>
<aside>
  <h1>Agricure database</h1>
  <p>{html.escape(db_label)}</p>
  {nav}
</aside>
<main>
  <header class="top">
    <h1>Database snapshot</h1>
    <p>Generated {generated} · read-only view. Re-run <code>scripts/view_database.py</code> to refresh.</p>
    <div class="stats">
      <div class="stat"><b>{len(tables)}</b> tables</div>
      <div class="stat"><b>{total_rows}</b> rows total</div>
      <div class="stat"><b>{limit}</b> rows max per table</div>
    </div>
  </header>
  {''.join(sections)}
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot the Agricure database to HTML")
    parser.add_argument("--limit", type=int, default=200, help="rows shown per table (default 200)")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    parser.add_argument("--out", default=OUT, help="output html path")
    args = parser.parse_args()

    is_sqlite = True
    db_label = ""
    conn = None

    sqlite_path = find_sqlite_db()
    if sqlite_path:
        conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        db_label = f"SQLite: {sqlite_path}"
        print(f"Reading SQLite database: {sqlite_path}")
        tables_list = list_tables_sqlite(conn)
    else:
        conn = connect_postgres()
        if conn is None:
            print("No database found. Start the backend once (or run database/seed.py) so the\n"
                  "SQLite demo database is created, then run this script again.")
            sys.exit(1)
        is_sqlite = False
        db_label = "PostgreSQL (DATABASE_URL)"
        print("Reading PostgreSQL database from DATABASE_URL")
        tables_list = list_tables_pg(conn)

    ordered = [t for t in PRIORITY_TABLES if t in tables_list]
    ordered += [t for t in tables_list if t not in ordered]

    tables = {}
    total_rows = 0
    for table in ordered:
        cols, rows = fetch(conn, table, args.limit, is_sqlite)
        total = count_rows(conn, table, is_sqlite)
        tables[table] = (cols, rows, total)
        total_rows += total
        print(f"  {table:24s} {total:>5} rows")

    html_out = build_html(db_label, tables, total_rows, args.limit)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html_out)
    print(f"\nWrote {args.out}  ({os.path.getsize(args.out) // 1024} KB)")

    if not args.no_open:
        webbrowser.open(f"file:///{os.path.abspath(args.out).replace(os.sep, '/')}")
        print("Opened it in your default browser.")


if __name__ == "__main__":
    main()
