# Testing Patterns

**Analysis Date:** 2026-02-14

## Test Framework

**Runner:**
- pytest 7.4.0+
- Config: No `pytest.ini` or `pyproject.toml` configuration file present
- Default pytest behavior used (discovers `test_*.py` and `*_test.py` files)

**Assertion Library:**
- pytest built-in assertions
- Simple `assert` statements for boolean checks
- Dataclass equality for model comparisons

**Run Commands:**
```bash
python -m pytest tests/ -v           # Run all tests with verbose output
python -m pytest tests/test_id_comparator.py -v  # Run specific test file
pytest tests/ -v --tb=short          # Run with short traceback format
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` directory at project root
- Separate from source code (not in `src/` alongside implementation)
- One test module per source module: `test_id_comparator.py`, `test_grade_store.py`, `test_notifications.py`

**Naming:**
- Files: `test_*.py` (pytest convention)
- Test functions: `test_<thing_being_tested>()` - all lowercase with underscores
- Test classes: `Test<Component>` - groups related tests
  - Example: `TestGradeStoreInitialization`, `TestSaveGradeData`, `TestRetrieveGradeData`

**Structure:**
```
tests/
├── test_id_comparator.py       # Tests for IDComparator and ChangeReport classes
├── test_grade_store.py         # Tests for GradeStore database layer
├── test_notifications.py       # Tests for notification managers and providers
├── test_fetch_grades.py        # Tests for API fetching
└── [dev/debug scripts]         # debug_comparator.py, simple_test.py, etc.
```

## Test Structure

**Suite Organization:**

```python
@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = GradeStore(db_path)
    yield store

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_grade_data():
    """Create sample grade data for testing"""
    assignment1 = Assignment(
        assignment_id="100",
        title="Test Assignment 1",
        earned_points=Decimal("5"),
        max_points=Decimal("5"),
        comment="Good work"
    )
    # ... build nested structure ...
    return GradeData(timestamp=datetime.now(), sections=[section])


def test_initial_data_capture(temp_db, sample_grade_data):
    """Test that initial data capture is detected correctly"""
    comparator = IDComparator(temp_db)
    report = comparator.detect_changes(sample_grade_data)
    assert report.is_initial is True
    assert report.has_changes() is False
```

**Patterns:**

- **Setup:** Fixtures create test data and temporary resources
  - `temp_db` - temporary SQLite database that cleans up after test
  - `sample_grade_data` - pre-built GradeData hierarchy with realistic nesting
  - `sample_assignment`, `sample_message` - smaller building blocks

- **Teardown:** Fixtures use `yield` with cleanup code after
  ```python
  yield store  # Test runs here
  Path(db_path).unlink(missing_ok=True)  # Cleanup
  ```

- **Assertion:** Simple `assert` statements for booleans, equality, membership
  ```python
  assert report.is_initial is True
  assert report.has_changes() is False
  assert len(report.changes) == 1
  assert report.grade_updates_count == 1
  assert "Initial" in report.summary()
  ```

- **Class grouping:** Related tests grouped in classes with descriptive names
  ```python
  class TestSaveGradeData:
      def test_save_creates_snapshot(self, temp_db, sample_grade_data):
      def test_save_stores_section(self, temp_db, sample_grade_data):
      def test_save_handles_null_values(self, temp_db):
  ```

## Mocking

**Framework:** `unittest.mock` from Python standard library

**Patterns:**

```python
from unittest.mock import Mock, patch, MagicMock

# Simple mock creation
with patch('notifications.pushover_provider.requests.post') as mock_post:
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'status': 1}
    provider = PushoverProvider(pushover_config)
    result = provider.send(sample_message)
    assert result is True
    mock_post.assert_called_once()

# Patching class methods
with patch.object(PushoverProvider, 'is_available', return_value=True):
    with patch.object(PushoverProvider, 'send', return_value=True):
        manager = NotificationManager(config)
        results = manager.send_notification(sample_message)
```

**What to Mock:**
- External API calls: `requests.post`, `genai.Client()`
- Provider `is_available()` checks - returns True/False to control provider loading
- Provider `send()` methods - returns True/False to simulate success/failure
- File I/O for non-unit tests - though integration tests may use real files

**What NOT to Mock:**
- Model creation and validation (Pydantic models work as is)
- Data structure operations (lists, dicts, dataclasses)
- Database operations in database-specific tests (tests use real temp SQLite)
- Notification message formatting (test actual format output)

**Provider availability pattern:**
```python
# Test that manager loads enabled providers
with patch.object(PushoverProvider, 'is_available', return_value=True):
    manager = NotificationManager(config)
assert 'pushover' in manager.get_available_providers()

# Test that unavailable providers are skipped
with patch.object(PushoverProvider, 'is_available', return_value=False):
    manager = NotificationManager(config)
assert 'pushover' not in manager.get_available_providers()
```

## Fixtures and Factories

**Test Data:**

Fixtures are hierarchical, building from small components:
```python
@pytest.fixture
def sample_assignment():
    """Create sample assignment"""
    return Assignment(
        assignment_id="100",
        title="Test Assignment",
        earned_points=Decimal("8"),
        max_points=Decimal("10"),
        exception=None,
        comment="Good work",
        due_date=datetime(2025, 1, 15, 23, 59)
    )

@pytest.fixture
def sample_grade_data(sample_assignment):
    """Create sample grade data structure"""
    category = Category(
        category_id=1,
        name="Homework",
        weight=Decimal("30"),
        assignments=[sample_assignment]
    )
    period = Period(period_id="sec1:T1", name="2024-2025 T1", categories=[category])
    section = Section(section_id="sec1", course_title="Math 7", section_title="Period 1", periods=[period])
    return GradeData(timestamp=datetime.now(), sections=[section])
```

**Fixture Scope:**
- Function scope (default) - fresh fixture for each test
- Fixtures used across test files have module-level scope
- Database fixtures always function-scoped with cleanup

**Location:**
- Fixtures in same file as tests they support
- Common fixtures duplicated across test files (no shared conftest)
- Location: `tests/` directory alongside test files

## Coverage

**Requirements:**
- No formal coverage requirements enforced
- No `.coverage` config or coverage reports in CI
- Tests exist for critical paths: change detection, storage, notifications

**View Coverage:**
```bash
pytest --cov=. tests/ --cov-report=html  # Generate HTML coverage report
pytest --cov=shared tests/               # Coverage for specific module
```

## Test Types

**Unit Tests:**
- Scope: Individual class/function in isolation
- Approach: Tests mock external dependencies, use temp databases
- Examples: `test_grade_change_detected()`, `test_parse_decimal()`, `test_send_makes_api_call()`
- Files: Majority of `tests/test_*.py` content

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Real database (temp SQLite), real Pydantic validation, mocked only external APIs
- Examples: `test_no_changes_detected()` (comparator + store), `test_gemini_runs_first_and_enhances_message()` (manager + providers)
- Files: Most of `test_notifications.py`, subset of `test_grade_store.py`

**E2E Tests:**
- Framework: Not formalized - `test_new_system.py` at project root is manual E2E
- Status: Not automated in test suite
- Approach: Manual testing with real API (currently run locally)

## Common Patterns

**Async Testing:**
Not used - all code is synchronous. No async/await patterns in pipeline.

**Error Testing:**

Exception validation pattern:
```python
def test_client_raises_on_missing_credentials():
    """Test that client raises ValueError if credentials missing"""
    with pytest.raises(ValueError) as exc_info:
        SchoologyAPIClient(api_key=None, api_secret=None)
    assert "API credentials not provided" in str(exc_info.value)
```

Graceful failure pattern:
```python
def test_send_handles_api_error(self, mock_post, pushover_config, sample_message):
    """Test that send handles API errors gracefully"""
    mock_post.return_value.status_code = 400
    provider = PushoverProvider(pushover_config)
    result = provider.send(sample_message)
    assert result is False  # Returns False, doesn't raise
```

**Null/None Handling:**

```python
def test_save_handles_null_values(self, temp_db):
    """Test that null/None values are stored correctly"""
    assignment = Assignment(
        assignment_id="200",
        title="Ungraded",
        earned_points=None,      # Test None for numeric fields
        max_points=None,
        exception=None,
        comment="No comment",
        due_date=None            # Test None for datetime field
    )
    # ... create and save ...
    assert row['earned_points'] is None
    assert row['max_points'] is None
    assert row['due_date'] is None
```

**Change Detection Testing Pattern:**

```python
def test_grade_change_detected(temp_db, sample_grade_data):
    """Test that grade changes are detected"""
    comparator = IDComparator(temp_db)

    # Step 1: Initial capture
    comparator.detect_changes(sample_grade_data)

    # Step 2: Modify data
    modified_data = GradeData(
        timestamp=datetime.now(),
        sections=sample_grade_data.sections
    )
    modified_data.sections[0].periods[0].categories[0].assignments[0].earned_points = Decimal("4")

    # Step 3: Detect change
    report = comparator.detect_changes(modified_data)

    # Step 4: Assert
    assert report.has_changes() is True
    assert report.grade_updates_count == 1
    assert len(report.changes) == 1
    change = report.changes[0]
    assert change.change_type == "grade_updated"
    assert change.old_grade == "5 / 5"
    assert change.new_grade == "4 / 5"
```

## Test Execution

**File locations:**
- `tests/test_id_comparator.py` - 300 lines, 9 tests
- `tests/test_grade_store.py` - 260 lines, 17 tests (grouped in 6 classes)
- `tests/test_notifications.py` - 325 lines, 25+ tests (grouped in 7 classes)
- `tests/test_fetch_grades.py` - Tests API fetching with mocked client

**Running specific test:**
```bash
python -m pytest tests/test_id_comparator.py::test_grade_change_detected -v
python -m pytest tests/test_grade_store.py::TestSaveGradeData -v
```

**Test isolation:**
- Each test uses fresh fixtures
- Temporary databases created and destroyed per test
- No shared state between tests
- Mocks reset automatically by pytest

---

*Testing analysis: 2026-02-14*
