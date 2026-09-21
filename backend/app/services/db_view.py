"""Read-only database snapshot rendered as a single HTML page.

Used by two callers:

* ``scripts/view_database.py`` — writes ``database_view.html`` for offline, no-app
  inspection (relative image paths).
* ``GET /api/admin/database-view`` — serves the same page to the signed-in admin
  (absolute image URLs, so thumbnails load inside a blob/new tab).

Works for both PostgreSQL and the SQLite demo fallback because it only uses
SQLAlchemy.
"""
import html
import json
import os
from datetime import datetime

from sqlalchemy import inspect, text

# Tables in the order an examiner would want to read them
PRIORITY_TABLES = [
    "users", "farms", "crop_reports", "agent_decisions", "agent_activity",
    "recommendations", "officer_verifications", "referrals", "sensor_readings",
    "notifications", "model_feedback", "model_versions", "audit_logs",
    "system_settings",
]

IMAGE_COLUMNS = ("image_path", "image_url")
JSON_COLUMNS = ("risk_factors", "factors", "metadata_json")
MAX_CELL_CHARS = 160


def _render_image(value: str, image_base: str | None, project_root: str) -> str:
    """A stored sample image, as a clickable thumbnail."""
    if value.startswith(("http://", "https://")):
        return f'<a href="{html.escape(value)}" target="_blank">{html.escape(value)}</a>'

    name = os.path.basename(value.replace("\\", "/"))
    if image_base:
        src = f"{image_base.rstrip('/')}/api/images/{name}"
    else:
        rel = value if not os.path.isabs(value) else os.path.relpath(value, project_root)
        rel = rel.replace("\\", "/")
        if not rel.startswith("backend/"):
            rel = "backend/" + rel.lstrip("./")
        src = rel
    return (
        f'<a href="{html.escape(src)}" target="_blank">'
        f'<img class="thumb" src="{html.escape(src)}" alt="crop sample" '
        f'onerror="this.replaceWith(document.createTextNode(\'file missing\'))"></a>'
    )


def _render_cell(column: str, value, image_base: str | None, project_root: str) -> str:
    if value is None:
        return '<span class="null">—</span>'
    if column in IMAGE_COLUMNS and isinstance(value, str) and value:
        return _render_image(value, image_base, project_root)
    text_value = str(value)
    if column in JSON_COLUMNS:
        try:
            text_value = json.dumps(json.loads(text_value), ensure_ascii=False)
        except Exception:
            pass
    if len(text_value) > MAX_CELL_CHARS:
        text_value = text_value[:MAX_CELL_CHARS] + "…"
    return html.escape(text_value)


def _table_section(name: str, columns: list[str], rows: list[tuple], total: int,
                   image_base: str | None, project_root: str, shown: int) -> str:
    if not columns:
        return (f'<section id="{name}"><h2>{html.escape(name)}</h2>'
                f'<p class="empty">No data.</p></section>')

    head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = "\n".join(
        "<tr>" + "".join(
            f"<td>{_render_cell(c, v, image_base, project_root)}</td>"
            for c, v in zip(columns, row)
        ) + "</tr>"
        for row in rows
    )
    note = ""
    if total > shown:
        note = f'<p class="note">Showing the first {shown} of {total} rows.</p>'
    return (
        f'<section id="{name}"><h2>{html.escape(name)} '
        f'<span class="count">{total} rows</span></h2>{note}'
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody></table></div></section>'
    )


STYLES = """
  :root { --forest:#1f3d2b; --forest-dark:#132920; --moss:#4f7942; --wheat:#d8a53d;
          --cream:#faf6ec; --cream-deep:#f1ead8; --ink:#14231a; --line:rgba(20,35,26,.12); }
  * { box-sizing:border-box; }
  body { margin:0; font-family:"Inter",-apple-system,Segoe UI,Roboto,sans-serif; color:var(--ink);
         background:var(--cream); display:flex; min-height:100vh; }
  aside { width:250px; flex-shrink:0; background:var(--forest-dark); color:#fff; padding:22px 16px;
          position:sticky; top:0; height:100vh; overflow-y:auto; }
  aside h1 { font-family:Georgia,serif; font-size:19px; margin:0 0 4px; font-weight:400; }
  aside p { font-size:11px; color:rgba(255,255,255,.6); margin:0 0 18px; word-break:break-all; }
  aside a { display:flex; justify-content:space-between; gap:8px; align-items:center;
            color:rgba(255,255,255,.85); text-decoration:none; font-size:13px;
            padding:7px 10px; border-radius:8px; }
  aside a:hover { background:rgba(255,255,255,.1); color:#fff; }
  .badge { background:var(--wheat); color:var(--forest-dark); font-size:10px; font-weight:700;
           padding:1px 7px; border-radius:999px; }
  main { flex:1; padding:26px 30px 60px; min-width:0; }
  header.top { border-bottom:1px solid var(--line); padding-bottom:16px; margin-bottom:22px; }
  header.top h1 { font-family:Georgia,serif; font-weight:400; margin:0 0 6px; color:var(--forest); }
  header.top p { margin:4px 0 0; font-size:13px; color:rgba(20,35,26,.6); }
  .stats { display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }
  .stat { background:#fff; border:1px solid var(--line); border-radius:10px; padding:8px 14px;
          font-size:12px; }
  .stat b { display:block; font-size:20px; font-family:Georgia,serif; color:var(--forest); }
  section { margin-bottom:34px; scroll-margin-top:16px; }
  section h2 { font-family:Georgia,serif; font-weight:400; font-size:20px; color:var(--forest);
               margin:0 0 8px; display:flex; align-items:center; gap:10px; }
  .count { font-family:inherit; font-size:11px; background:var(--cream-deep); color:var(--moss);
           border-radius:999px; padding:2px 9px; font-weight:600; }
  .scroll { overflow-x:auto; background:#fff; border:1px solid var(--line); border-radius:10px; }
  table { border-collapse:collapse; font-size:12px; width:100%; }
  th, td { text-align:left; padding:7px 11px; border-bottom:1px solid var(--line);
           vertical-align:top; white-space:nowrap; }
  th { background:var(--cream-deep); position:sticky; top:0; font-weight:600; font-size:11px;
       text-transform:uppercase; letter-spacing:.04em; color:rgba(20,35,26,.6); }
  tbody tr:hover { background:rgba(79,121,66,.06); }
  .null { color:rgba(20,35,26,.3); }
  .thumb { width:52px; height:52px; object-fit:cover; border-radius:7px;
           border:1px solid var(--line); display:block; }
  .note, .empty { font-size:12px; color:rgba(20,35,26,.55); margin:0 0 8px; }
  a { color:var(--moss); }
"""


def generate_database_view(engine, *, limit: int = 200, image_base: str | None = None,
                           project_root: str | None = None, db_label: str | None = None) -> str:
    """Return a complete HTML page listing every table and its rows (read-only)."""
    project_root = project_root or os.getcwd()
    inspector = inspect(engine)
    found = inspector.get_table_names()

    ordered = [t for t in PRIORITY_TABLES if t in found] + [t for t in sorted(found) if t not in PRIORITY_TABLES]

    sections = []
    nav_items = []
    totals = {"rows": 0, "tables": 0}

    with engine.connect() as conn:
        for table in ordered:
            columns = [c["name"] for c in inspector.get_columns(table)]
            rows = conn.execute(text(f'SELECT * FROM "{table}" LIMIT {int(limit)}')).fetchall()
            total = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0
            totals["rows"] += total
            totals["tables"] += 1
            nav_items.append(
                f'<a href="#{table}">{html.escape(table)} <span class="badge">{total}</span></a>'
            )
            sections.append(_table_section(table, columns, rows, total, image_base,
                                           project_root, len(rows)))

    generated = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    # never print a real password in the page header
    safe_url = str(engine.url)
    if engine.url.password:
        safe_url = safe_url.replace(engine.url.password, "***")
    label = db_label or safe_url

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Agricure database view</title>
<style>{STYLES}</style>
</head>
<body>
<aside>
  <h1>Agricure database</h1>
  <p>{html.escape(str(label))}</p>
  {''.join(nav_items)}
</aside>
<main>
  <header class="top">
    <h1>Database view</h1>
    <p>Generated {generated} · read-only snapshot. Individual reports are grouped per user in
       the Admin → All Samples &amp; Reports tab.</p>
    <div class="stats">
      <div class="stat"><b>{totals['tables']}</b> tables</div>
      <div class="stat"><b>{totals['rows']}</b> rows total</div>
      <div class="stat"><b>{limit}</b> rows max per table</div>
    </div>
  </header>
  {''.join(sections)}
</main>
</body>
</html>
"""
