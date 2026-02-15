# Coding Conventions

**Analysis Date:** 2026-02-14

## Naming Patterns

**Files:**
- Lowercase with underscores: `fetch_grades_v2.py`, `id_comparator.py`, `grade_store.py`
- Version numbers in names when replacing older versions: `orchestrator_v2.py`, `fetch_grades_v2.py`
- Test files prefixed with `test_`: `test_id_comparator.py`, `test_grade_store.py`

**Classes:**
- PascalCase: `APIGradeFetcherV2`, `GradeStore`, `IDComparator`, `NotificationProvider`, `CircuitBreaker`
- Meaningful descriptive names: `ChangeReport`, `GradeChange`, `SchoologyAPIClient`
- Exception classes inherit from base pipeline exceptions: `ScrapingError(PipelineError)`, `ComparisonError(PipelineError)`

**Functions:**
- snake_case: `parse_scrape_times()`, `retry_with_backoff()`, `setup_logging()`, `detect_changes()`
- Private functions prefixed with underscore: `_compare_grade_data()`, `_parse_grade()`, `_get_connection()`
- Dataclass fields use snake_case: `assignment_id`, `earned_points`, `max_points`, `exception`

**Variables:**
- snake_case: `last_exception`, `max_retries`, `pipeline_duration`, `notification_results`
- Boolean prefixes: `is_initial`, `has_changes`, `enable_change_logging`, `force_save_on_error`
- Collection suffixes: `changes` (list), `results` (dict), `counts` (dict)

**Types:**
- Pydantic models use PascalCase: `Assignment`, `Category`, `Period`, `Section`, `GradeData`
- Dataclasses use PascalCase: `GradeChange`, `ChangeReport`, `NotificationMessage`
- Enum members use UPPER_CASE: `RetryStrategy.FIXED`, `RetryStrategy.EXPONENTIAL`

## Code Style

**Formatting:**
- Python 3.10+ standard style (implicit line continuations, match expressions)
- Type hints throughout: explicit return types on all functions
- Docstrings: module-level, class-level, and method-level docstrings
- Triple-quoted strings for all docstrings and multi-line strings

**Linting:**
- No formal linter enforced
- Code follows PEP 8 conventions implicitly
- Type hints used extensively (all functions annotated)

**Example pattern:**
```python
def detect_changes(self, new_data: GradeData, save_to_db: bool = True) -> ChangeReport:
    """
    Detect changes by comparing new data against database.

    Args:
        new_data: New grade data to compare
        save_to_db: Whether to save new data to database after comparison

    Returns:
        ChangeReport with all detected changes
    """
```

## Import Organization

**Order:**
1. Standard library imports: `logging`, `datetime`, `sys`, `json`, `sqlite3`, `time`, `functools`
2. Third-party imports: `requests`, `requests_oauthlib`, `pydantic`, `tomli`, `google.genai`, `dotenv`
3. Local imports: `from api.client import`, `from shared.models import`, `from pipeline.`

**Path Aliases:**
- None used - absolute imports from root: `from shared.models import GradeData`
- Relative imports used within packages: `from .models import Assignment` (in `shared/` package)

**No wildcard imports** - all imports are explicit and specific.

## Error Handling

**Patterns:**

Custom exception hierarchy for pipeline errors:
```python
class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass

class ScrapingError(PipelineError):
    """Scraping-specific errors"""
    pass

class ComparisonError(PipelineError):
    """Change detection errors"""
    pass

class NotificationError(PipelineError):
    """Notification delivery errors"""
    pass
```

Context managers for resource cleanup:
```python
@contextmanager
def _get_connection(self):
    """Context manager for database connections"""
    conn = sqlite3.connect(self.db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

Try-except with logging and fallback:
```python
try:
    data = self._get(endpoint)
    return data.get('assignment', [])
except Exception as e:
    logger.warning(f"Could not parse grade value: {grade}")
    return None
```

Generic exception catching used strategically:
- `except:` in validators used to catch any parse errors: `except: return None`
- Bare `except Exception as e:` with re-raise in pipeline context managers
- Specific exception handling in retry logic: `except exceptions as e:`

## Logging

**Framework:** Python `logging` module

**Patterns:**
- Logger created per module: `logging.getLogger(__name__)`
- Logger instance stored in `__init__`: `self.logger = logging.getLogger(__name__)`
- Standardized format with timestamp: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`

**Log Levels:**
- `logger.info()` - major pipeline steps: "Starting grade monitoring pipeline", "Step 1: Fetching grades"
- `logger.debug()` - detailed operations: enrollment ID fallbacks, detailed exception handling
- `logger.warning()` - recoverable issues: "Failed to send change notification", "Could not parse due date"
- `logger.error()` - serious failures: unrecoverable errors

**Example:**
```python
self.logger.info("Comparing new data against database...")
self.logger.warning(f"Could not parse grade value: {grade}")
self.logger.error(f"Failed to write change log: {e}")
```

## Comments

**When to Comment:**
- Complex algorithms or non-obvious logic: section ID offset matching, exception code mapping
- API-specific details: exception codes (0=none, 1=excused, 2=incomplete, 3=missing)
- Gotchas: "Only consider comment changes if they're substantive (not 'No comment')"

**JSDoc/TSDoc:**
- Docstrings provide full documentation
- Type hints replace parameter type documentation
- Return types explicitly specified in function signature

**Example pattern:**
```python
@field_validator('exception', mode='before')
@classmethod
def parse_exception(cls, v):
    """Map exception codes to strings

    Codes:
    - 0 = no exception
    - 1 = excused
    - 2 = incomplete
    - 3 = missing
    """
```

## Function Design

**Size:**
- Most functions 20-60 lines (includes docstring and type hints)
- Longer methods (100+ lines) refactored into smaller helpers with leading underscore
- Example: `_compare_grade_data()` is 60 lines, calls into `_get_assignment_comment()`, `_parse_grade()`

**Parameters:**
- Methods use `self` as first parameter
- Type hints on all parameters
- Default arguments used for optional config: `db_path: str = "data/grades.db"`
- Keyword-only arguments after `*` when needed
- `Optional[Type]` for nullable parameters

**Return Values:**
- Explicit return type annotations: `-> ChangeReport`, `-> bool`, `-> list[GradeChange]`
- Multiple returns of same type allowed: `report = ChangeReport(...); return report`
- None as explicit return for void operations
- Union types rare - typically `Optional[Type]` instead of `Union[Type, None]`

**Example:**
```python
def _parse_grade(self, grade_obj: Dict[str, Any]) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
    """Parse grade value from API into normalized components."""
```

## Module Design

**Exports:**
- All public classes and functions are direct imports
- No `__all__` declarations used
- Modules directly importable: `from shared.models import GradeData`

**Barrel Files:**
- `__init__.py` files exist but are mostly empty
- Each module imported directly by full path
- Example: `from shared.models import GradeData` not `from shared import GradeData`

**Organization:**
- `shared/` - core domain models and utilities used across pipeline
- `api/` - API client and grade fetching logic
- `pipeline/` - orchestration and cross-cutting concerns
- `notifications/` - plugin-based notification providers
- `tests/` - test suite following module structure

---

*Convention analysis: 2026-02-14*
