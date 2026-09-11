"""
Tests for point-in-time grade history and change-log backfill.
"""
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from shared.models import Assignment, Category, Period, Section, GradeData
from shared.grade_store import GradeStore

from scripts.backfill_history import build_snapshots, load_entries, parse_grade_string


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = GradeStore(db_path)
    yield store

    Path(db_path).unlink(missing_ok=True)


def make_grade_data(timestamp: datetime, earned, *, assignment_id="100", max_points="10",
                    exception=None, section_id="sec1") -> GradeData:
    """Build a one-assignment GradeData tree at a given point in time"""
    assignment = Assignment(
        assignment_id=assignment_id,
        title="Essay",
        earned_points=earned,
        max_points=max_points,
        exception=exception,
        comment="No comment",
    )
    return GradeData(
        timestamp=timestamp,
        sections=[Section(
            section_id=section_id,
            course_title="Math 7",
            section_title="Period 1",
            periods=[Period(
                period_id=f"{section_id}:T1",
                name="2024-2025 T1",
                categories=[Category(
                    category_id=1,
                    name="Homework",
                    weight=Decimal("30"),
                    assignments=[assignment],
                )],
            )],
        )],
    )


class TestHistoryRecording:
    """History rows accumulate instead of overwriting"""

    def test_each_save_appends_a_history_row(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7")))
        temp_db.save_grade_data(make_grade_data(base + timedelta(days=1), Decimal("9")))

        history = temp_db.get_assignment_history("100")

        assert [point.earned_points for point in history] == [Decimal("7"), Decimal("9")]
        assert [point.recorded_at for point in history] == [base, base + timedelta(days=1)]

    def test_current_state_still_holds_only_latest(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7")))
        temp_db.save_grade_data(make_grade_data(base + timedelta(days=1), Decimal("9")))

        assert temp_db.get_assignment("100").earned_points == Decimal("9")

    def test_history_carries_labels(self, temp_db):
        temp_db.save_grade_data(make_grade_data(datetime(2025, 1, 1, 8, 0), Decimal("7")))

        point = temp_db.get_assignment_history("100")[0]

        assert point.title == "Essay"
        assert point.section_name == "Math 7: Period 1"
        assert point.period_name == "2024-2025 T1"
        assert point.category_name == "Homework"

    def test_percentage_computed_from_points(self, temp_db):
        temp_db.save_grade_data(make_grade_data(datetime(2025, 1, 1, 8, 0), Decimal("8")))

        assert temp_db.get_assignment_history("100")[0].percentage() == pytest.approx(80.0)

    def test_exception_recorded_without_points(self, temp_db):
        temp_db.save_grade_data(
            make_grade_data(datetime(2025, 1, 1, 8, 0), None, exception="Missing")
        )

        point = temp_db.get_assignment_history("100")[0]

        assert point.exception == "Missing"
        assert point.percentage() is None

    def test_history_can_be_disabled(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            store = GradeStore(db_path, history_enabled=False)
            store.save_grade_data(make_grade_data(datetime(2025, 1, 1, 8, 0), Decimal("7")))

            assert store.get_assignment_history("100") == []
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_history_survives_section_pruning(self, temp_db):
        """A course that ends must not take its history with it"""
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7"), section_id="old"))

        # Next feed reports a different section entirely; "old" gets pruned
        temp_db.save_grade_data(make_grade_data(
            base + timedelta(days=1), Decimal("9"), assignment_id="200", section_id="new"
        ))

        assert temp_db.get_section("old") is None
        assert temp_db.get_assignment("100") is None

        history = temp_db.get_assignment_history("100")
        assert len(history) == 1
        assert history[0].earned_points == Decimal("7")
        assert history[0].section_name == "Math 7: Period 1"


class TestHistoryQueries:
    """Read paths a scrubbing dashboard depends on"""

    def test_get_history_at_carries_last_value_forward(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7")))
        temp_db.save_grade_data(make_grade_data(base + timedelta(days=5), Decimal("9")))

        midway = temp_db.get_history_at(base + timedelta(days=2))

        assert len(midway) == 1
        assert midway[0].earned_points == Decimal("7")

    def test_get_history_at_before_any_data_is_empty(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7")))

        assert temp_db.get_history_at(base - timedelta(days=1)) == []

    def test_get_history_at_picks_latest_per_assignment(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7")))
        temp_db.save_grade_data(make_grade_data(base + timedelta(days=1), Decimal("8")))
        temp_db.save_grade_data(make_grade_data(base + timedelta(days=2), Decimal("9")))

        current = temp_db.get_history_at(base + timedelta(days=10))

        assert len(current) == 1
        assert current[0].earned_points == Decimal("9")

    def test_assignment_history_respects_bounds(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        for day, points in enumerate(["5", "6", "7", "8"]):
            temp_db.save_grade_data(make_grade_data(base + timedelta(days=day), Decimal(points)))

        window = temp_db.get_assignment_history(
            "100", since=base + timedelta(days=1), until=base + timedelta(days=2)
        )

        assert [point.earned_points for point in window] == [Decimal("6"), Decimal("7")]

    def test_snapshot_times_are_chronological(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base + timedelta(days=1), Decimal("7")))
        temp_db.save_grade_data(make_grade_data(base, Decimal("5")))

        times = [timestamp for _, timestamp in temp_db.get_snapshot_times()]

        assert times == sorted(times)


class TestSnapshotRetention:
    """Retention governs history, so it must be opt-in"""

    def test_unlimited_by_default(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        for day in range(5):
            temp_db.save_grade_data(make_grade_data(base + timedelta(days=day), Decimal("7")))

        assert len(temp_db.get_snapshot_times()) == 5

    def test_retention_prunes_oldest_history_first(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            store = GradeStore(db_path, snapshot_retention=2)
            base = datetime(2025, 1, 1, 8, 0)
            for day, points in enumerate(["5", "6", "7"]):
                store.save_grade_data(make_grade_data(base + timedelta(days=day), Decimal(points)))

            history = store.get_assignment_history("100")

            assert len(store.get_snapshot_times()) == 2
            assert [point.earned_points for point in history] == [Decimal("6"), Decimal("7")]
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_latest_snapshot_time_uses_timestamp_not_insert_order(self, temp_db):
        """Backfill inserts old snapshots last; they must not look like the latest"""
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("7")))
        temp_db.append_history_snapshot(
            base - timedelta(days=30), [{"assignment_id": "100", "earned_points": Decimal("3")}]
        )

        assert temp_db.get_latest_snapshot_time() == base


class TestAppendHistorySnapshot:
    """The backfill entry point"""

    def test_writes_history_without_touching_current_state(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("9")))

        temp_db.append_history_snapshot(base - timedelta(days=1), [{
            "assignment_id": "100",
            "title": "Essay",
            "earned_points": Decimal("4"),
            "max_points": Decimal("10"),
        }])

        assert temp_db.get_assignment("100").earned_points == Decimal("9")
        assert [p.earned_points for p in temp_db.get_assignment_history("100")] == [
            Decimal("4"), Decimal("9")
        ]

    def test_rerunning_same_timestamp_corrects_instead_of_duplicating(self, temp_db):
        base = datetime(2025, 1, 1, 8, 0)
        record = {"assignment_id": "100", "title": "Essay", "earned_points": Decimal("4")}

        temp_db.append_history_snapshot(base, [record])
        temp_db.append_history_snapshot(base, [{**record, "earned_points": Decimal("5")}])

        history = temp_db.get_assignment_history("100")
        assert len(history) == 1
        assert history[0].earned_points == Decimal("5")
        assert len(temp_db.get_snapshot_times()) == 1

    def test_empty_records_is_a_noop(self, temp_db):
        assert temp_db.append_history_snapshot(datetime(2025, 1, 1, 8, 0), []) is None
        assert temp_db.get_snapshot_times() == []

    def test_live_labels_win_over_backfilled_blanks(self, temp_db):
        """A backfill without IDs must not blank out labels the pipeline knows"""
        base = datetime(2025, 1, 1, 8, 0)
        temp_db.save_grade_data(make_grade_data(base, Decimal("9")))

        temp_db.append_history_snapshot(base - timedelta(days=1), [{
            "assignment_id": "100",
            "title": "Essay",
            "earned_points": Decimal("4"),
        }])

        assert temp_db.get_assignment_history("100")[0].section_id == "sec1"


class TestGradeStringParsing:
    """Inverting Assignment.grade_string() for backfill"""

    @pytest.mark.parametrize("text,earned,max_points", [
        ("8 / 10", Decimal("8"), Decimal("10")),
        ("8/10", Decimal("8"), Decimal("10")),
        ("8.5 / 10", Decimal("8.5"), Decimal("10")),
        ("7", Decimal("7"), None),
    ])
    def test_parses_point_values(self, text, earned, max_points):
        parsed = parse_grade_string(text)

        assert parsed["earned_points"] == earned
        assert parsed["max_points"] == max_points
        assert parsed["exception"] is None

    @pytest.mark.parametrize("text", ["Missing", "Excused", "Incomplete", "missing"])
    def test_parses_exceptions(self, text):
        parsed = parse_grade_string(text)

        assert parsed["exception"] == text.title()
        assert parsed["earned_points"] is None

    @pytest.mark.parametrize("text", [None, "", "Not graded", "not graded", "wat", "x / y"])
    def test_rejects_unusable_values(self, text):
        assert parse_grade_string(text) is None


class TestBackfill:
    """Replaying the change log into history"""

    def write_log(self, tmp_path: Path, entries: list[dict]) -> Path:
        log_file = tmp_path / "grade_changes.log"
        log_file.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n")
        return log_file

    def change(self, **overrides) -> dict:
        change = {
            "assignment_id": "100",
            "assignment_title": "Essay",
            "section": "Math 7: Period 1",
            "period": "2024-2025 T1",
            "category": "Homework",
            "change_type": "grade_updated",
            "old_grade": "7 / 10",
            "new_grade": "9 / 10",
        }
        change.update(overrides)
        return change

    def test_builds_one_snapshot_per_log_entry(self, tmp_path):
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-01T08:00:00", "changes": [self.change(new_grade="7 / 10")]},
            {"timestamp": "2025-01-02T08:00:00", "changes": [self.change(new_grade="9 / 10")]},
        ]))

        snapshots, unparseable = build_snapshots(entries, seed_initial=False)

        assert unparseable == 0
        assert len(snapshots) == 2
        assert snapshots[datetime(2025, 1, 2, 8, 0)][0]["earned_points"] == Decimal("9")

    def test_entries_are_sorted_oldest_first(self, tmp_path):
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-05T08:00:00", "changes": []},
            {"timestamp": "2025-01-01T08:00:00", "changes": []},
        ]))

        assert entries[0]["_parsed_timestamp"] < entries[1]["_parsed_timestamp"]

    def test_malformed_lines_are_skipped(self, tmp_path):
        log_file = tmp_path / "grade_changes.log"
        log_file.write_text(
            '{"timestamp": "2025-01-01T08:00:00", "changes": []}\n'
            'not json at all\n'
            '{"no_timestamp": true}\n'
        )

        assert len(load_entries(log_file)) == 1

    def test_initial_entries_contribute_nothing(self, tmp_path):
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-01T08:00:00", "is_initial": True, "changes": []},
        ]))

        snapshots, _ = build_snapshots(entries, seed_initial=False)

        assert snapshots == {}

    def test_unparseable_grades_are_counted_and_skipped(self, tmp_path):
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-01T08:00:00", "changes": [self.change(new_grade="???")]},
        ]))

        snapshots, unparseable = build_snapshots(entries, seed_initial=False)

        assert unparseable == 1
        assert snapshots == {}

    def test_seed_initial_records_prior_value_before_the_window(self, tmp_path):
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-02T08:00:00", "changes": [self.change()]},
        ]))

        snapshots, _ = build_snapshots(entries, seed_initial=True)

        seed_time = datetime(2025, 1, 2, 8, 0) - timedelta(seconds=1)
        assert snapshots[seed_time][0]["earned_points"] == Decimal("7")
        assert snapshots[datetime(2025, 1, 2, 8, 0)][0]["earned_points"] == Decimal("9")

    def test_seed_initial_skips_new_assignments(self, tmp_path):
        """A new assignment has no prior value to seed"""
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-02T08:00:00",
             "changes": [self.change(change_type="new_assignment", old_grade=None)]},
        ]))

        snapshots, _ = build_snapshots(entries, seed_initial=True)

        assert len(snapshots) == 1

    def test_backfilled_series_is_queryable(self, temp_db, tmp_path):
        """End to end: log -> history -> scrub query"""
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-01T08:00:00", "changes": [self.change(new_grade="7 / 10")]},
            {"timestamp": "2025-01-10T08:00:00", "changes": [self.change(new_grade="9 / 10")]},
        ]))
        snapshots, _ = build_snapshots(entries, seed_initial=False)

        for timestamp in sorted(snapshots):
            temp_db.append_history_snapshot(timestamp, snapshots[timestamp])

        midway = temp_db.get_history_at(datetime(2025, 1, 5))

        assert len(midway) == 1
        assert midway[0].earned_points == Decimal("7")
        assert midway[0].percentage() == pytest.approx(70.0)
        assert midway[0].section_name == "Math 7: Period 1"

    def test_seed_initial_ignores_later_events(self, tmp_path):
        """Only the first event speaks to the pre-window state"""
        entries = load_entries(self.write_log(tmp_path, [
            {"timestamp": "2025-01-01T08:00:00",
             "changes": [self.change(change_type="new_assignment", old_grade=None,
                                     new_grade="7 / 10")]},
            {"timestamp": "2025-01-02T08:00:00",
             "changes": [self.change(old_grade="7 / 10", new_grade="9 / 10")]},
        ]))

        snapshots, _ = build_snapshots(entries, seed_initial=True)

        # Two observed snapshots, no synthetic seed before them
        assert sorted(snapshots) == [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 2, 8, 0)]
