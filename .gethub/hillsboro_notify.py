#!/usr/bin/env python3
"""
Hillsboro Yard notification sender (North + South, Day + Night).

- Reads the relevant roster file for each yard/shift from the repository:
    North Day:   data.json
    North Night: data-night.json
    South Day:   south-yard-assignments-day.json
    South Night: south-yard-assignments.json
- Sends scheduled Day/Night summaries at 9:00 AM / 9:00 PM America/Chicago,
  for both yards.
- Sends an immediate notification when the relevant data file changes.
- Each email embeds a real screenshot of the live report page (rendered with
  the current data), not just a text summary; text is kept as a plaintext
  fallback for accessibility / non-HTML mail clients.
- North Crystal Sugar recipients are OFF until 2026-10-01 (crystal_sugar
  config section). South Yard recipients are a simple on/off switch
  (south_yard config section), off by default until configured.
- A one-time Day test can be enabled per yard in notification-config.json.
"""
import argparse, datetime as dt, functools, hashlib, json, os, re, smtplib, ssl, subprocess, threading
from email.message import EmailMessage
from email.utils import formataddr
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "notification-config.json"
STATE = ROOT / ".notification-state.json"
TZ = ZoneInfo("America/Chicago")
REPO_PAGES = "https://justinperris.github.io/Beet-Harvest-North-Hillsboro-Yard-day/"

DATA_PATH = {
    ("north", "day"): ROOT / "data.json",
    ("north", "night"): ROOT / "data-night.json",
    ("south", "day"): ROOT / "south-yard-assignments-day.json",
    ("south", "night"): ROOT / "south-yard-assignments.json",
}
PAGE_FOR = {
    ("north", "day"): "hillsboro-signin.html",
    ("north", "night"): "hillsboro-signin-Night.html",
    ("south", "day"): "south-yard-crew-report-Day.html",
    ("south", "night"): "south-yard-crew-report.html",
}
YARD_LABEL = {"north": "Hillsboro North Yard", "south": "South Yard"}
CONFIG_SECTION = {"north": "crystal_sugar", "south": "south_yard"}

# South Yard's report page fetches its data straight from GitHub's raw CDN
# (rather than a same-origin relative fetch like the North Yard page), so a
# route intercept is used to serve the freshly-checked-out local copy instead
# of whatever the CDN currently has cached.
SOUTH_REMOTE_FILE_RE = {
    "day": re.compile(r"south-yard-assignments-day\.json"),
    "night": re.compile(r"south-yard-assignments\.json"),
}

def page_url_for(yard, shift):
    return REPO_PAGES + PAGE_FOR[(yard, shift)]

def data_path_for(yard, shift):
    return DATA_PATH[(yard, shift)]

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def role_for(row):
    if row.get("operator"): return "Operator"
    if row.get("relief"): return "Relief"
    if row.get("boom"): return "Boom"
    if row.get("foreman"): return "Foreman"
    if row.get("skidsteer"): return "Skid"
    if row.get("loader"): return "Loader"
    return None

def group_rows_north(rows):
    piler7, piler8, unassigned, hidden = [], [], [], []
    for row in rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        if row.get("hidden"):
            hidden.append(name)
            continue
        role = role_for(row)
        entry = f"{name} ({role})" if role else name
        piler = str(row.get("piler") or "").strip()
        if piler == "7":
            piler7.append(entry)
        elif piler == "8":
            piler8.append(entry)
        else:
            unassigned.append(entry)
    return piler7, piler8, unassigned, hidden

def summary_north(data, shift):
    rows = data.get("rows") or []
    piler7, piler8, unassigned, hidden = group_rows_north(rows)
    location = data.get("location") or "Hillsboro Yard North"
    date = data.get("date") or "Not set"
    day_label = (data.get("day") or "").strip()
    notes = (data.get("notes") or "").strip()

    header = f"{location} — {date}" + (f" — {day_label}" if day_label else "")
    total = len(piler7) + len(piler8) + len(unassigned)

    lines = [f"Hillsboro North Yard — {shift.upper()}", header, "",
             f"Total crew on roster: {total}", "",
             f"Piler #7 ({len(piler7)}): " + (", ".join(piler7) if piler7 else "none assigned"),
             f"Piler #8 ({len(piler8)}): " + (", ".join(piler8) if piler8 else "none assigned")]
    if unassigned:
        lines.append(f"Unassigned ({len(unassigned)}): " + ", ".join(unassigned))
    if hidden:
        lines.append(f"Hidden/removed entries: {len(hidden)}")
    if notes:
        lines += ["", f"Notes: {notes}"]
    lines += ["", "View the current sign-in:", page_url_for("north", shift)]
    return "\n".join(lines)

def group_assignments_south(assignments):
    pilers, foreman, skid_loader, extra, hidden = {}, [], [], [], []
    for a in assignments:
        name = (a.get("name") or "").strip()
        if not name:
            continue
        if a.get("hidden"):
            hidden.append(name)
            continue
        role = role_for(a)
        entry = f"{name} ({role})" if role else name
        piler = a.get("piler")
        if a.get("foreman"):
            foreman.append(entry)
        elif a.get("skidsteer") or a.get("loader"):
            skid_loader.append(entry)
        elif piler is not None:
            pilers.setdefault(piler, []).append(entry)
        else:
            extra.append(entry)
    return pilers, foreman, skid_loader, extra, hidden

def summary_south(data, shift):
    assignments = data.get("assignments") or []
    pilers, foreman, skid_loader, extra, hidden = group_assignments_south(assignments)
    last_updated = data.get("lastUpdated") or "Not set"
    notes = (data.get("notes") or "").strip()
    total = sum(len(v) for v in pilers.values()) + len(foreman) + len(skid_loader) + len(extra)

    lines = [f"South Yard — {shift.upper()}", f"Last updated: {last_updated}", "",
             f"Total crew on roster: {total}", ""]
    for num in sorted(pilers.keys()):
        entries = pilers[num]
        lines.append(f"Piler #{num} ({len(entries)}): " + ", ".join(entries))
    if foreman:
        lines.append(f"Yard Foreman ({len(foreman)}): " + ", ".join(foreman))
    if skid_loader:
        lines.append(f"Skid Steer/Loader ({len(skid_loader)}): " + ", ".join(skid_loader))
    if extra:
        lines.append(f"Extra People ({len(extra)}): " + ", ".join(extra))
    if hidden:
        lines.append(f"Out today: {len(hidden)}")
    if notes:
        lines += ["", f"Notes: {notes}"]
    lines += ["", "View the current report:", page_url_for("south", shift)]
    return "\n".join(lines)

def summary_for(yard, data, shift):
    return summary_north(data, shift) if yard == "north" else summary_south(data, shift)

def render_page_png(yard, shift):
    """Screenshots the real report page (with today's data loaded) so the email
    can show an actual static copy of the page instead of a hand-built summary.
    Returns None on any failure so the caller can fall back to text-only rather
    than lose the notification entirely."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("Playwright not available, skipping screenshot:", e)
        return None

    page_file = PAGE_FOR[(yard, shift)]
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{httpd.server_port}/{page_file}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1400, "height": 1000})

            if yard == "south":
                local_path = data_path_for("south", shift)
                pattern = SOUTH_REMOTE_FILE_RE[shift]
                def handle_route(route):
                    if local_path.exists() and pattern.search(route.request.url):
                        route.fulfill(status=200, content_type="application/json",
                                       body=local_path.read_text(encoding="utf-8"))
                    else:
                        route.continue_()
                page.route(re.compile(r"raw\.githubusercontent\.com"), handle_route)

            page.goto(url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(600)
            png_bytes = page.screenshot(full_page=True)
            browser.close()
        return png_bytes
    except Exception as e:
        print("Screenshot failed, falling back to text-only email:", e)
        return None
    finally:
        httpd.shutdown()

def recipients(cfg, yard, shift, now, one_time=False):
    out = list(cfg.get("test_recipients", [])) if cfg.get("test_enabled", True) else []
    section = cfg.get(CONFIG_SECTION[yard], {})
    if yard == "north":
        enabled_from = cfg.get("crystal_sugar_enabled_from", "2026-10-01")
    else:
        enabled_from = section.get("enabled_from", "2026-10-01")
    enabled = now.date() >= dt.date.fromisoformat(enabled_from)
    if shift == "day":
        if (enabled and section.get("day_enabled", False)) or one_time:
            out += section.get("day_recipients", [])
    else:
        if enabled and section.get("night_enabled", False):
            out += section.get("night_recipients", [])
    return list(dict.fromkeys(out))

def send_email(subject, body, to_list, image_bytes=None, page_url=None, sender_name=None):
    if not to_list:
        print("No recipients enabled; nothing sent.")
        return
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_APP_PASSWORD"]
    msg = EmailMessage()
    msg["From"] = formataddr((sender_name, user)) if sender_name else user
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject
    msg.set_content(body)

    if image_bytes:
        html_body = (
            "<html><body style=\"font-family:sans-serif;\">"
            f"<p><a href=\"{page_url}\">Open the live report page</a></p>"
            "<img src=\"cid:signin-snapshot\" style=\"max-width:100%;border:1px solid #ccc;\">"
            "</body></html>"
        )
        msg.add_alternative(html_body, subtype="html")
        html_part = msg.get_payload()[-1]
        html_part.add_related(image_bytes, maintype="image", subtype="png", cid="signin-snapshot")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    print("Sent:", to_list)

def data_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_state(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

def maybe_commit_state():
    # The workflow grants GITHUB_TOKEN. State changes are excluded from the push trigger.
    subprocess.run(["git", "config", "user.name", "hillsboro-notifications[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", ".notification-state.json", "notification-config.json"], check=False)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", "Update notification state"], check=True)
        subprocess.run(["git", "push"], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", choices=["change", "schedule", "test"], required=True)
    ap.add_argument("--yard", choices=["north", "south"], default="north")
    ap.add_argument("--shift", choices=["day", "night"], required=True)
    args = ap.parse_args()

    cfg = load_json(CONFIG, {})
    state = load_json(STATE, {})
    now = dt.datetime.now(TZ)
    section_key = CONFIG_SECTION[args.yard]

    # One-time Day test: enable in config (per yard), run --event test, then auto-disable.
    one_time = args.event == "test" and args.shift == "day" and cfg.get(section_key, {}).get("day_test_once", False)

    if args.event == "schedule":
        hour = now.hour
        expected = 9 if args.shift == "day" else 21
        if hour != expected:
            print("Not the scheduled local hour; exiting.")
            return
        key = f"{now.date()}-{args.yard}-{args.shift}"
        if state.get("last_scheduled") == key:
            print("Scheduled report already sent.")
            return
        state["last_scheduled"] = key

    data_path = data_path_for(args.yard, args.shift)

    if args.event == "change":
        h = data_hash(data_path)
        hash_key = f"last_data_hash_{args.yard}_{args.shift}"
        if state.get(hash_key) == h:
            print("No data change detected.")
            return
        state[hash_key] = h

    body = summary_for(args.yard, load_json(data_path, {}), args.shift)
    label = YARD_LABEL[args.yard]
    subject = f"{label} — {args.shift.title()} {'Update' if args.event != 'schedule' else 'Report'}"
    to = recipients(cfg, args.yard, args.shift, now, one_time=one_time)
    page_url = page_url_for(args.yard, args.shift)
    image_bytes = render_page_png(args.yard, args.shift)
    send_email(subject, body, to, image_bytes=image_bytes, page_url=page_url,
               sender_name=cfg.get("sender_name"))

    if one_time:
        cfg.setdefault(section_key, {})["day_test_once"] = False
        CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    save_state(state)
    if one_time:
        maybe_commit_state()

if __name__ == "__main__":
    main()
