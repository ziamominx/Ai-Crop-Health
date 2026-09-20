"""Generate a single self-contained HTML snapshot of the Agricure database.

No app to install: this reads the SQLite demo database (or PostgreSQL if
DATABASE_URL points at one), writes `database_view.html` in the project root and
opens it in your default browser. Stored crop samples are shown as thumbnails.

The same page is available inside the app at
Admin → "Open database view" (served by GET /api/admin/database-view).

Run:
    backend/.venv/Scripts/python scripts/view_database.py
    backend/.venv/Scripts/python scripts/view_database.py --no-open
    backend/.venv/Scripts/python scripts/view_database.py --limit 500
"""
import argparse
import os
import sys
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

OUT = os.path.join(ROOT, "database_view.html")


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot the Agricure database to HTML")
    parser.add_argument("--limit", type=int, default=200, help="rows shown per table (default 200)")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    parser.add_argument("--out", default=OUT, help="output html path")
    args = parser.parse_args()

    # The backend resolves its SQLite path (and reads backend/.env) relative to the
    # directory it is launched from, so step into backend/ first — otherwise we'd
    # read (or create) an empty database in the project root instead.
    backend_dir = os.path.join(ROOT, "backend")
    os.chdir(backend_dir)

    from app.database import _is_fallback_db, engine  # imports create/warn as the app does
    from app.services.db_view import generate_database_view

    db_name = engine.url.database
    label = ("SQLite demo fallback" if _is_fallback_db else "PostgreSQL") + f" · {db_name}"
    print(f"Reading database: {os.path.abspath(db_name) if _is_fallback_db else db_name}")

    if _is_fallback_db and not os.path.exists(db_name):
        print("\nThat SQLite database does not exist yet. Start the backend once, or create the\n"
              "demo data with:  cd backend && .venv/Scripts/python ../database/seed.py")
        sys.exit(1)

    page = generate_database_view(
        engine,
        limit=max(10, args.limit),
        image_base=None,          # file mode: relative paths resolve from the project root
        project_root=ROOT,
        db_label=label,
    )

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"Wrote {args.out}  ({os.path.getsize(args.out) // 1024} KB)")

    if not args.no_open:
        webbrowser.open(f"file:///{os.path.abspath(args.out).replace(os.sep, '/')}")
        print("Opened it in your default browser.")


if __name__ == "__main__":
    main()
