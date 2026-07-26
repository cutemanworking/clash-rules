#!/usr/bin/env python3
"""
Clash Rules Sync Script
Fetches upstream rules from dler-io/Rules and masnmarc/broker-rules.
Updates local YAML files safely with format validation.
"""

import sys
import urllib.request
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Upstream URL Mappings
DLER_ROOT_BASE = "https://raw.githubusercontent.com/dler-io/Rules/master/Clash/Provider/"
DLER_MEDIA_BASE = "https://raw.githubusercontent.com/dler-io/Rules/master/Clash/Provider/Media/"

SPECIAL_SOURCES = {
    "Broker.yaml": "https://raw.githubusercontent.com/masnmarc/broker-rules/main/rule/Clash/Broker/Broker.yaml"
}


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP status {response.status}")
        return response.read().decode("utf-8")


def is_valid_rule_file(content: str) -> bool:
    if not content or len(content.strip()) < 10:
        return False
    # Standard Clash rule-provider files contain 'payload:'
    if "payload:" in content or "DOMAIN" in content or "IP-CIDR" in content:
        return True
    return False


def sync_file(file_path: Path, url: str) -> str:
    """
    Syncs a single file. Returns status: 'updated', 'unchanged', or 'failed'.
    """
    try:
        new_content = fetch_url(url)
        if not is_valid_rule_file(new_content):
            print(f"[FAIL] {file_path.relative_to(REPO_ROOT)}: Invalid rule content received")
            return "failed"

        existing_content = file_path.read_text("utf-8") if file_path.exists() else ""
        if existing_content == new_content:
            return "unchanged"

        file_path.write_text(new_content, "utf-8")
        return "updated"

    except Exception as e:
        print(f"[FAIL] {file_path.relative_to(REPO_ROOT)}: {e}")
        return "failed"


def main():
    root_files = sorted([p.name for p in REPO_ROOT.glob("*.yaml")])
    media_dir = REPO_ROOT / "Media"
    media_files = sorted([p.name for p in media_dir.glob("*.yaml")]) if media_dir.exists() else []

    total_files = len(root_files) + len(media_files)
    print(f"Starting sync for {total_files} rule files...\n")

    updated = []
    unchanged = []
    failed = []

    # Sync Root Files
    for filename in root_files:
        file_path = REPO_ROOT / filename
        if filename in SPECIAL_SOURCES:
            url = SPECIAL_SOURCES[filename]
        else:
            url = f"{DLER_ROOT_BASE}{urllib.parse.quote(filename)}"

        status = sync_file(file_path, url)
        if status == "updated":
            updated.append(filename)
        elif status == "unchanged":
            unchanged.append(filename)
        else:
            failed.append(filename)

    # Sync Media Files
    for filename in media_files:
        file_path = media_dir / filename
        url = f"{DLER_MEDIA_BASE}{urllib.parse.quote(filename)}"

        status = sync_file(file_path, url)
        if status == "updated":
            updated.append(f"Media/{filename}")
        elif status == "unchanged":
            unchanged.append(f"Media/{filename}")
        else:
            failed.append(f"Media/{filename}")

    print("\n" + "=" * 40)
    print(f"Sync Summary: Total={total_files}")
    print(f"  Updated:   {len(updated)}")
    print(f"  Unchanged: {len(unchanged)}")
    print(f"  Failed:    {len(failed)}")
    print("=" * 40)

    if updated:
        print("\nUpdated files:")
        for f in updated:
            print(f"  - {f}")

    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)

    print("\nSync completed successfully!")


if __name__ == "__main__":
    main()
