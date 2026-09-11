#!/usr/bin/env python3
"""
Backfill assignment_history from the JSON change log.

The history table only starts collecting from the day it is enabled. This
script recovers what came before by replaying logs/grade_changes.log, which
records every detected change with its old and new grade strings.

Limitations worth knowing before you trust a chart built on backfilled data:

- The log only records *changes*, so the series is sparse. A value holds until
  the next recorded change; read it as a step function, not as a sample per run.
- The log keeps `change_log_retention_days` (default 90) of history. Anything
  older is already gone.
- Grades are stored in the log as display strings ("8 / 10", "Missing"), so
  they are parsed back rather than read as numbers. Anything unparseable is
  reported and skipped.
- Assignments graded once before the log window opened, and never touched
  since, do not appear at all.

Usage:
    python scripts/backfill_history.py --dry-run
    python scripts/backfill_history.py
    python scripts/backfill_history.py --db data/grades.db --log logs/grade_changes.log
"""
import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.grade_store import GradeStore

logger = logging.getLogger("backfill_history")

# Exception values Assignment.grade_string() emits verbatim
EXCEPTION_VALUES = {"missing", "excused", "incomplete"}


def parse_grade_string(grade: Optional[str]) -> Optional[dict]:
    """
    Invert Assignment.grade_string().

    Returns a dict with earned_points / max_points / exception, or None if the
    string is absent or not recognizable.
    """
    if grade is None:
        return None

    text = grade.strip()
    if not text or text.lower() == "not graded":
        return None

    if text.lower() in EXCEPTION_VALUES:
        # Exceptions carry no points; the title-cased form matches the model
        return {"earned_points": None, "max_points": None, "exception": text.title()}

    if "/" in text:
        earned_text, _, max_text = text.partition("/")
        try:
            return {
                "earned_points": Decimal(earned_text.strip()),
                "max_points": Decimal(max_text.strip()),
                "exception": None,
            }
        except InvalidOperation:
            return None

    try:
        return {"earned_points": Decimal(text), "max_points": None, "exception": None}
    except InvalidOperation:
        return None


def load_entries(log_file: Path) -> list[dict]:
    """Read the change log, skipping malformed lines, oldest entry first."""
    entries = []
    malformed = 0

    with open(log_file, "r") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry["_parsed_timestamp"] = datetime.fromisoformat(entry["timestamp"])
                entries.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                malformed += 1
                logger.warning(f"Skipping malformed log line {line_no}")

    if malformed:
        logger.warning(f"Skipped {malformed} malformed log line(s)")

    entries.sort(key=lambda e: e["_parsed_timestamp"])
    return entries


def build_snapshots(entries: list[dict], seed_initial: bool) -> tuple[dict, int]:
    """
    Turn change-log entries into per-timestamp history records.

    Args:
        entries: Change-log entries, oldest first
        seed_initial: Also record each assignment's pre-change value at the
            earliest log timestamp. This is inferred, not observed: it says
            "the grade was already this when our records begin", which is true
            of the value but not of the timestamp.

    Returns:
        (mapping of timestamp -> list of history records, count of unparseable grades)
    """
    snapshots: dict[datetime, dict[str, dict]] = defaultdict(dict)
    unparseable = 0
    seeds: dict[str, dict] = {}
    seen: set[str] = set()

    earliest = entries[0]["_parsed_timestamp"] if entries else None

    for entry in entries:
        timestamp = entry["_parsed_timestamp"]

        for change in entry.get("changes", []):
            assignment_id = change.get("assignment_id")
            if not assignment_id:
                continue

            labels = {
                "assignment_id": assignment_id,
                "title": change.get("assignment_title"),
                "section_name": change.get("section"),
                "period_name": change.get("period"),
                "category_name": change.get("category"),
            }

            parsed = parse_grade_string(change.get("new_grade"))
            if parsed is None and change.get("new_grade"):
                if str(change["new_grade"]).strip().lower() != "not graded":
                    unparseable += 1
                    logger.warning(
                        f"Unparseable grade {change['new_grade']!r} for "
                        f"{change.get('assignment_title', assignment_id)} at {timestamp}"
                    )
                    continue

            record = dict(labels)
            record.update(parsed or {"earned_points": None, "max_points": None, "exception": None})
            snapshots[timestamp][assignment_id] = record

            # Only an assignment's *first* event says anything about the state
            # before the log window. A later event's old_grade is a value we
            # already recorded, not a pre-window one.
            if seed_initial and assignment_id not in seen:
                prior = parse_grade_string(change.get("old_grade"))
                if prior is not None:
                    seed = dict(labels)
                    seed.update(prior)
                    seeds[assignment_id] = seed

            seen.add(assignment_id)

    # Seeds land one second before the earliest real entry so they never
    # collide with, or override, an observed value at that timestamp.
    if seed_initial and seeds and earliest is not None:
        seed_time = earliest - timedelta(seconds=1)
        for assignment_id, record in seeds.items():
            snapshots[seed_time].setdefault(assignment_id, record)

    return {ts: list(records.values()) for ts, records in snapshots.items()}, unparseable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="data/grades.db", help="Path to the SQLite database")
    parser.add_argument("--log", default="logs/grade_changes.log", help="Path to the JSON change log")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be written, write nothing")
    parser.add_argument(
        "--seed-initial",
        action="store_true",
        help="Also record each assignment's pre-change grade at the start of the log window. "
             "The value is real but the timestamp is inferred.",
    )
    parser.add_argument("--verbose", action="store_true", help="Log every snapshot written")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    log_file = Path(args.log)
    if not log_file.exists():
        logger.error(f"Change log not found: {log_file}")
        return 1

    entries = load_entries(log_file)
    if not entries:
        logger.error(f"No usable entries in {log_file}")
        return 1

    logger.info(
        f"Read {len(entries)} log entries spanning "
        f"{entries[0]['_parsed_timestamp']} to {entries[-1]['_parsed_timestamp']}"
    )

    snapshots, unparseable = build_snapshots(entries, seed_initial=args.seed_initial)
    total_records = sum(len(records) for records in snapshots.values())
    assignments = {r["assignment_id"] for records in snapshots.values() for r in records}

    logger.info(
        f"Reconstructed {total_records} history row(s) across {len(snapshots)} snapshot(s) "
        f"for {len(assignments)} assignment(s)"
    )
    if unparseable:
        logger.warning(f"{unparseable} grade value(s) could not be parsed and were skipped")

    if args.dry_run:
        for timestamp in sorted(snapshots):
            logger.info(f"  would write {len(snapshots[timestamp])} row(s) at {timestamp}")
        logger.info("Dry run: nothing written")
        return 0

    # Retention is left unlimited here; pruning is the live pipeline's job and
    # would otherwise delete the backfilled snapshots we are about to insert.
    store = GradeStore(args.db, history_enabled=True, snapshot_retention=0)

    written = 0
    for timestamp in sorted(snapshots):
        records = snapshots[timestamp]
        snapshot_id = store.append_history_snapshot(timestamp, records)
        written += len(records)
        logger.debug(f"Wrote {len(records)} row(s) at {timestamp} (snapshot {snapshot_id})")

    logger.info(f"Backfill complete: {written} history row(s) written to {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
