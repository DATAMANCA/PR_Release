import html
import json
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv

from emailer import send_email
from sources import fetch_all

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "seen.json"
CONFIG_PATH = ROOT / "config" / "watchlist.yaml"
MAX_SEEN = 5000

load_dotenv(ROOT / ".env")


def load_seen() -> list[str]:
    if STATE_PATH.exists() and STATE_PATH.read_text().strip():
        return json.loads(STATE_PATH.read_text())
    return []


def save_seen(seen_ids: list[str]) -> None:
    trimmed = seen_ids[-MAX_SEEN:]
    STATE_PATH.write_text(json.dumps(trimmed, indent=0))


def load_keyword_patterns() -> list[tuple[str, re.Pattern]]:
    """Compile each watchlist term into a whole-word/phrase regex.

    Plain substring matching would let "Visa Inc" match inside "visa increase",
    or "Tesla Inc" inside "tesla increased" - confirmed in testing. Word
    boundaries prevent a keyword from matching as part of a longer word while
    still matching normal punctuation-adjacent usage like "Visa Inc." or
    "Visa Inc,".
    """
    config = yaml.safe_load(CONFIG_PATH.read_text())
    keywords = []
    for terms in config.get("watchlist", {}).values():
        keywords.extend(terms)
    return [(kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)) for kw in keywords]


def find_match(item: dict, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    text = f"{item['title']} {item['summary']}"
    for kw, pattern in patterns:
        if pattern.search(text):
            return kw
    return None


def build_email_body(matches: list[dict]) -> str:
    rows = []
    for m in matches:
        rows.append(
            "<p><b>[{kw}] {title}</b><br>"
            "Source: {source} | Published: {published}<br>"
            "<a href='{link}'>{link}</a></p>".format(
                kw=html.escape(m["matched_keyword"]),
                title=html.escape(m["title"]),
                source=html.escape(m["source"]),
                published=html.escape(m["published"]),
                link=html.escape(m["link"]),
            )
        )
    return "\n".join(rows)


def main() -> None:
    seen_list = load_seen()
    seen_set = set(seen_list)
    is_bootstrap = len(seen_set) == 0

    patterns = load_keyword_patterns()
    items = fetch_all()
    print(f"Fetched {len(items)} total items across all sources.")

    new_matches = []
    pending_seen = []
    for item in items:
        item_id = item["id"]
        if item_id in seen_set:
            continue
        seen_set.add(item_id)  # avoid double-processing the same item within this run

        kw = find_match(item, patterns)
        if kw and not is_bootstrap:
            # Held back from pending_seen on purpose: only persisted as "seen"
            # after send_email() succeeds below, so a failed send gets retried
            # next run instead of silently vanishing.
            item["matched_keyword"] = kw
            new_matches.append(item)
        else:
            pending_seen.append(item_id)

    seen_list.extend(pending_seen)
    save_seen(seen_list)

    if is_bootstrap:
        print(f"Bootstrap run: seeded {len(seen_set)} known items, no email sent.")
        return

    if new_matches:
        subject = f"Newswire Watch: {len(new_matches)} new match(es)"
        send_email(subject, build_email_body(new_matches))
        seen_list.extend(item["id"] for item in new_matches)
        save_seen(seen_list)
        print(f"Sent email with {len(new_matches)} match(es).")
    else:
        print("No new matches this run.")


if __name__ == "__main__":
    main()
