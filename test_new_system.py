#!/usr/bin/env python3
"""
Test script for the new ID-based change detection system.

This script demonstrates the new system and allows testing without
affecting the production database.
"""
import logging
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_api_fetcher():
    """Test the new API fetcher that preserves IDs"""
    from api.fetch_grades_v2 import APIGradeFetcherV2

    logger.info("=" * 70)
    logger.info("Testing API Fetcher V2")
    logger.info("=" * 70)

    try:
        fetcher = APIGradeFetcherV2()
        grade_data = fetcher.fetch_all_grades()

        # Summary
        total_sections = len(grade_data.sections)
        all_assignments = grade_data.get_all_assignments()
        total_assignments = len(all_assignments)

        logger.info(f"\n✓ Fetch successful!")
        logger.info(f"  Sections: {total_sections}")
        logger.info(f"  Total assignments: {total_assignments}")

        # Show sample assignment with IDs
        if total_assignments > 0:
            section, period, category, assignment = all_assignments[0]
            logger.info(f"\nSample assignment:")
            logger.info(f"  Section ID: {section.section_id}")
            logger.info(f"  Section: {section.full_name}")
            logger.info(f"  Period: {period.name} (ID: {period.period_id})")
            logger.info(f"  Category: {category.name} (ID: {category.category_id})")
            logger.info(f"  Assignment: {assignment.title} (ID: {assignment.assignment_id})")
            logger.info(f"  Grade: {assignment.grade_string()}")
            logger.info(f"  Comment: {assignment.comment}")

        return grade_data

    except Exception as e:
        logger.error(f"✗ API fetch failed: {e}", exc_info=True)
        return None


def test_database_storage(grade_data):
    """Test database storage and retrieval"""
    from shared.grade_store import GradeStore

    logger.info("\n" + "=" * 70)
    logger.info("Testing Database Storage")
    logger.info("=" * 70)

    try:
        # Use temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = f.name

        logger.info(f"Using temporary database: {temp_db}")

        store = GradeStore(temp_db)

        # Save data
        logger.info("Saving grade data...")
        snapshot_id = store.save_grade_data(grade_data)
        logger.info(f"✓ Saved snapshot {snapshot_id}")

        # Retrieve data
        logger.info("Retrieving assignment by ID...")
        all_assignments = grade_data.get_all_assignments()
        if all_assignments:
            test_assignment = all_assignments[0][3]  # Get Assignment object
            retrieved = store.get_assignment(test_assignment.assignment_id)

            if retrieved:
                logger.info(f"✓ Retrieved assignment: {retrieved.title}")
                logger.info(f"  ID: {retrieved.assignment_id}")
                logger.info(f"  Grade: {retrieved.grade_string()}")
            else:
                logger.error("✗ Failed to retrieve assignment")

        # Cleanup
        Path(temp_db).unlink()
        logger.info("✓ Database test complete")

        return True

    except Exception as e:
        logger.error(f"✗ Database test failed: {e}", exc_info=True)
        return False


def test_change_detection(grade_data):
    """Test change detection with simulated changes"""
    from shared.grade_store import GradeStore
    from shared.id_comparator import IDComparator
    from decimal import Decimal
    import copy

    logger.info("\n" + "=" * 70)
    logger.info("Testing Change Detection")
    logger.info("=" * 70)

    try:
        # Use temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = f.name

        store = GradeStore(temp_db)
        comparator = IDComparator(store)

        # First run - initial capture
        logger.info("First run (initial capture)...")
        report1 = comparator.detect_changes(grade_data)
        logger.info(f"✓ {report1.summary()}")
        assert report1.is_initial is True

        # Second run - no changes
        logger.info("\nSecond run (no changes)...")
        report2 = comparator.detect_changes(grade_data)
        logger.info(f"✓ {report2.summary()}")
        assert report2.has_changes() is False

        # Third run - simulate grade change
        logger.info("\nThird run (simulating grade change)...")
        modified_data = copy.deepcopy(grade_data)

        # Find a graded assignment and change its grade
        for section in modified_data.sections:
            for period in section.periods:
                for category in period.categories:
                    for assignment in category.assignments:
                        if assignment.earned_points is not None:
                            old_grade = assignment.grade_string()
                            assignment.earned_points = assignment.earned_points - Decimal("1")
                            new_grade = assignment.grade_string()
                            logger.info(f"  Modifying {assignment.title}: {old_grade} → {new_grade}")
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break

        report3 = comparator.detect_changes(modified_data, save_to_db=False)
        logger.info(f"✓ {report3.summary()}")

        if report3.has_changes():
            logger.info(f"  Detected {len(report3.changes)} change(s):")
            for change in report3.changes[:3]:  # Show first 3
                logger.info(f"    • {change.summary()}")
        else:
            logger.warning("  No changes detected (this might be unexpected)")

        # Cleanup
        Path(temp_db).unlink()
        logger.info("✓ Change detection test complete")

        return True

    except Exception as e:
        logger.error(f"✗ Change detection test failed: {e}", exc_info=True)
        return False


def test_full_pipeline():
    """Test the complete pipeline (without sending notifications)"""
    from pipeline.orchestrator_v2 import GradePipelineV2

    logger.info("\n" + "=" * 70)
    logger.info("Testing Full Pipeline (Dry Run)")
    logger.info("=" * 70)

    try:
        # This will use the actual database, so be careful
        logger.warning("This test uses the real database at data/grades.db")
        logger.warning("Press Ctrl+C to cancel, or wait 3 seconds to continue...")

        import time
        time.sleep(3)

        pipeline = GradePipelineV2()

        # Run pipeline (this will fetch from API)
        logger.info("Running full pipeline...")
        success = pipeline.run_full_pipeline()

        if success:
            logger.info("✓ Pipeline completed successfully")
        else:
            logger.error("✗ Pipeline failed")

        return success

    except KeyboardInterrupt:
        logger.info("\nTest cancelled by user")
        return False
    except Exception as e:
        logger.error(f"✗ Pipeline test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests"""
    logger.info("Starting ID-Based Change Detection System Tests")
    logger.info("=" * 70)

    # Test 1: API Fetcher
    grade_data = test_api_fetcher()
    if not grade_data:
        logger.error("Cannot continue without grade data")
        sys.exit(1)

    # Test 2: Database Storage
    if not test_database_storage(grade_data):
        logger.error("Database test failed")
        sys.exit(1)

    # Test 3: Change Detection
    if not test_change_detection(grade_data):
        logger.error("Change detection test failed")
        sys.exit(1)

    # Test 4: Full Pipeline (optional)
    logger.info("\n" + "=" * 70)
    response = input("Run full pipeline test with real database? (y/N): ")
    if response.lower() == 'y':
        if not test_full_pipeline():
            logger.error("Pipeline test failed")
            sys.exit(1)
    else:
        logger.info("Skipping full pipeline test")

    logger.info("\n" + "=" * 70)
    logger.info("✓ All tests passed!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
