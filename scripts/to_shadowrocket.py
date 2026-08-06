#!/usr/bin/env python3
"""Convert Clash rule-provider YAML files to Shadowrocket rule lists."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "shadowrocket"

# Clash rule types that map 1:1 to Shadowrocket
SUPPORTED = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "IP-CIDR",
    "IP-CIDR6",
    "GEOIP",
    "USER-AGENT",
    "URL-REGEX",
    "PROCESS-NAME",
    "DST-PORT",
    "SRC-PORT",
    "PROTOCOL",
}


def convert_line(line: str) -> str | None:
    """Convert a single Clash payload line to Shadowrocket format."""
    stripped = line.strip()

    if not stripped:
        return ""

    # Keep comments (including commented-out rules)
    if stripped.startswith("#"):
        # "# - RULE" -> "# RULE"
        body = stripped[1:].strip()
        if body.startswith("- "):
            body = body[2:].strip()
        return f"# {body}" if body else "#"

    # Active rule: "- TYPE,value" or "- TYPE,value,no-resolve"
    if stripped.startswith("- "):
        rule = stripped[2:].strip()
    else:
        rule = stripped

    if not rule or rule == "payload:":
        return None

    # Skip YAML list under payload that is just structural
    rule_type = rule.split(",", 1)[0].strip().upper()
    if rule_type not in SUPPORTED:
        return f"# unsupported: {rule}"

    return rule


def convert_file(src: Path, dst: Path) -> tuple[int, int]:
    """Convert one YAML file. Returns (kept, skipped)."""
    kept = 0
    skipped = 0
    out_lines: list[str] = []
    in_payload = False

    for raw in src.read_text("utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped == "payload:":
            in_payload = True
            continue

        if not in_payload:
            # Allow files that are already bare rule lists
            if stripped.startswith("- ") or stripped.startswith("#"):
                in_payload = True
            else:
                continue

        result = convert_line(line)
        if result is None:
            skipped += 1
            continue
        if result.startswith("# unsupported:"):
            skipped += 1
            out_lines.append(result)
            continue

        out_lines.append(result)
        if result and not result.startswith("#"):
            kept += 1

    # Trim trailing empty lines, ensure single trailing newline
    while out_lines and out_lines[-1] == "":
        out_lines.pop()

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), "utf-8")
    return kept, skipped


def main() -> None:
    yaml_files = sorted(REPO_ROOT.rglob("*.yaml"))
    # Exclude nothing under scripts; only convert rule YAMLs at root and Media/
    targets = [
        p
        for p in yaml_files
        if p.is_relative_to(REPO_ROOT)
        and "scripts" not in p.parts
        and ".git" not in p.parts
        and "shadowrocket" not in p.parts
    ]

    print(f"Converting {len(targets)} files -> {OUT_DIR.relative_to(REPO_ROOT)}/\n")

    total_kept = 0
    total_skipped = 0

    for src in targets:
        rel = src.relative_to(REPO_ROOT)
        # Shadowrocket lists commonly use .list extension
        dst = OUT_DIR / rel.with_suffix(".list")
        kept, skipped = convert_file(src, dst)
        total_kept += kept
        total_skipped += skipped
        print(f"  {rel} -> {dst.relative_to(REPO_ROOT)}  (+{kept} rules)")

    print(f"\nDone. rules={total_kept}, skipped/unsupported={total_skipped}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
