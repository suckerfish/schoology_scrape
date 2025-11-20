#!/usr/bin/env python3
"""
Fetch grade data from Schoology API with ID preservation.

This module fetches grade data and returns it in the new GradeData model format,
preserving all unique identifiers from the API for efficient change detection.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from decimal import Decimal
from api.client import SchoologyAPIClient
from shared.models import Assignment, Category, Period, Section, GradeData


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class APIGradeFetcherV2:
    """Fetches grade data from API and returns GradeData models with IDs preserved"""

    def __init__(self):
        self.client = SchoologyAPIClient()
        self.sections_cache = {}
        self.categories_cache = {}
        self.assignments_cache = {}
        self.enrollment_id_map = {}  # Maps grade_section_id -> enrollment_section_id

    def _parse_grade(self, grade_obj: Dict[str, Any]) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
        """
        Parse grade value from API into normalized components.

        Args:
            grade_obj: Grade object from API

        Returns:
            Tuple of (earned_points, max_points, exception)

        Note:
            Exception field values:
            - 0 = no exception
            - 1 = excused
            - 2 = incomplete
            - 3 = missing
        """
        grade = grade_obj.get('grade')
        max_points = grade_obj.get('max_points')
        exception = grade_obj.get('exception', 0)

        # Map exception codes to strings
        exception_map = {
            1: 'Excused',
            2: 'Incomplete',
            3: 'Missing'
        }
        exception_str = exception_map.get(exception)

        # Parse numeric values
        earned = None
        max_pts = None

        if exception_str is None:  # No exception
            if grade is not None and grade != '':
                try:
                    earned = Decimal(str(grade))
                except:
                    logger.warning(f"Could not parse grade value: {grade}")

            if max_points is not None and max_points != '':
                try:
                    max_pts = Decimal(str(max_points))
                except:
                    logger.warning(f"Could not parse max_points value: {max_points}")

        return earned, max_pts, exception_str

    def _parse_timestamp(self, timestamp: int) -> datetime:
        """Convert Unix timestamp to datetime"""
        if not timestamp:
            return None
        return datetime.fromtimestamp(timestamp)

    def _parse_due_date(self, due_date_str: str) -> Optional[datetime]:
        """Parse due date string from API"""
        if not due_date_str:
            return None

        try:
            # API format: YYYY-MM-DD HH:MM:SS
            return datetime.strptime(due_date_str, '%Y-%m-%d %H:%M:%S')
        except:
            logger.warning(f"Could not parse due date: {due_date_str}")
            return None

    def _get_assignment_comment(self, section_id: str, assignment_id: str, grade_obj: Dict[str, Any]) -> str:
        """
        Get comment for assignment.

        Priority:
        1. Comment from grade data
        2. Comments from assignment discussion endpoint
        """
        # Check grade object for teacher comment
        if grade_obj.get('comment'):
            return grade_obj['comment']

        # Try to get from comments endpoint
        comments = self.client.get_assignment_comments(section_id, assignment_id)
        if comments:
            # Return most recent comment
            sorted_comments = sorted(comments, key=lambda x: x.get('created', 0), reverse=True)
            return sorted_comments[0].get('comment', 'No comment')

        return 'No comment'

    def _get_assignment_title(self, grade_section_id: str, assignment_id: str) -> str:
        """Get assignment title from cache or API"""
        cache_key = f"{grade_section_id}:{assignment_id}"

        if cache_key not in self.assignments_cache:
            enrollment_id = self.enrollment_id_map.get(grade_section_id, grade_section_id)

            assignment = None

            # Try enrollment ID
            if enrollment_id != grade_section_id:
                try:
                    assignment = self.client.get_assignment_details(enrollment_id, assignment_id)
                    logger.debug(f"Fetched assignment {assignment_id} using enrollment ID {enrollment_id}")
                except Exception as e:
                    logger.debug(f"Could not fetch with enrollment ID {enrollment_id}: {e}")

            # Fall back to grade section ID
            if not assignment:
                try:
                    assignment = self.client.get_assignment_details(grade_section_id, assignment_id)
                    logger.debug(f"Fetched assignment {assignment_id} using grade section ID {grade_section_id}")
                except Exception as e:
                    logger.warning(f"Could not fetch assignment {assignment_id} with either ID: {e}")

            if assignment:
                self.assignments_cache[cache_key] = assignment
            else:
                self.assignments_cache[cache_key] = {'title': f'Assignment {assignment_id}'}

        return self.assignments_cache[cache_key].get('title', f'Assignment {assignment_id}')

    def _get_assignment_due_date(self, section_id: str, assignment_id: str) -> Optional[datetime]:
        """Get assignment due date as datetime"""
        cache_key = f"{section_id}:{assignment_id}"

        if cache_key in self.assignments_cache:
            assignment = self.assignments_cache[cache_key]
            due_date_str = assignment.get('due', '')
            return self._parse_due_date(due_date_str)

        return None

    def _get_category_info(self, grade_section_id: str, category_id: int) -> Tuple[str, Optional[Decimal]]:
        """Get category name and weight"""
        if grade_section_id not in self.categories_cache:
            enrollment_id = self.enrollment_id_map.get(grade_section_id, grade_section_id)

            categories = None

            # Try enrollment ID
            if enrollment_id != grade_section_id:
                try:
                    categories = self.client.get_grading_categories(enrollment_id)
                    logger.debug(f"Fetched categories using enrollment ID {enrollment_id}")
                except Exception as e:
                    logger.debug(f"Could not fetch categories with enrollment ID: {e}")

            # Fall back to grade section ID
            if not categories:
                try:
                    categories = self.client.get_grading_categories(grade_section_id)
                except Exception as e:
                    logger.warning(f"Could not fetch categories for section {grade_section_id}: {e}")
                    categories = []

            self.categories_cache[grade_section_id] = {
                cat['id']: cat for cat in categories
            }

        category = self.categories_cache[grade_section_id].get(category_id, {})
        name = category.get('title', f'Category {category_id}')
        weight = category.get('weight')

        weight_decimal = None
        if weight is not None:
            try:
                weight_decimal = Decimal(str(weight))
            except:
                pass

        return name, weight_decimal

    def fetch_all_grades(self) -> GradeData:
        """
        Fetch all grade data from API.

        Returns:
            GradeData model with all sections, periods, categories, and assignments
        """
        logger.info("Fetching sections...")
        sections_list = self.client.get_sections()
        logger.info(f"Found {len(sections_list)} sections")

        # Get all grades
        logger.info("Fetching all grades...")
        all_grades = self.client.get_grades()

        # Build mapping of enrollment IDs
        section_map = {}
        for section_data in sections_list:
            enrollment_id = section_data['id']
            course_title = section_data.get('course_title', 'Unknown Course')
            section_title = section_data.get('section_title', '')
            section_map[enrollment_id] = {
                'course_title': course_title,
                'section_title': section_title,
                'enrollment_id': enrollment_id
            }

        # Process grades and build Section models
        sections = []

        for section_grades in all_grades.get('section', []):
            grade_section_id = section_grades['section_id']

            # Match section info
            section_info = section_map.get(grade_section_id)
            matched_enrollment_id = None

            if not section_info:
                # Try to match by offset (known API quirk)
                logger.warning(f"Section ID {grade_section_id} not in sections list, trying to match...")
                for offset in [-1, 1, -2, 2]:
                    nearby_id = str(int(grade_section_id) + offset)
                    if nearby_id in section_map:
                        logger.info(f"  Matched {grade_section_id} to {nearby_id} (offset {offset})")
                        section_info = section_map[nearby_id]
                        matched_enrollment_id = nearby_id
                        break

            if not section_info:
                logger.warning(f"  Could not match section {grade_section_id}, using generic name")
                section_info = {
                    'course_title': 'Unknown Course',
                    'section_title': f'Section {grade_section_id}',
                    'enrollment_id': grade_section_id
                }
                matched_enrollment_id = grade_section_id
            elif matched_enrollment_id is None:
                matched_enrollment_id = section_info.get('enrollment_id', grade_section_id)

            # Store mapping for detail fetches
            self.enrollment_id_map[grade_section_id] = matched_enrollment_id

            logger.info(f"Processing {section_info['course_title']}... (grade_id={grade_section_id})")

            # Create Section model
            section = Section(
                section_id=grade_section_id,
                course_title=section_info['course_title'],
                section_title=section_info['section_title']
            )

            # Process each grading period
            for period_data in section_grades.get('period', []):
                period_title = period_data.get('period_title', 'Unknown Period')

                # Create Period model
                period = Period(
                    period_id=f"{grade_section_id}:{period_title}",  # Composite key
                    name=period_title
                )

                # Group assignments by category
                category_assignments = defaultdict(list)

                for assignment_grade in period_data.get('assignment', []):
                    assignment_id = str(assignment_grade['assignment_id'])
                    category_id = assignment_grade.get('category_id', 0)

                    # Parse grade components
                    earned, max_pts, exception = self._parse_grade(assignment_grade)

                    # Get assignment details
                    title = self._get_assignment_title(grade_section_id, assignment_id)
                    comment = self._get_assignment_comment(grade_section_id, assignment_id, assignment_grade)
                    due_date = self._get_assignment_due_date(grade_section_id, assignment_id)

                    # Create Assignment model
                    assignment = Assignment(
                        assignment_id=assignment_id,
                        title=title,
                        earned_points=earned,
                        max_points=max_pts,
                        exception=exception,
                        comment=comment,
                        due_date=due_date
                    )

                    # Group by category
                    category_assignments[category_id].append(assignment)

                # Create Category models
                for category_id, assignments in category_assignments.items():
                    category_name, category_weight = self._get_category_info(grade_section_id, category_id)

                    category = Category(
                        category_id=category_id,
                        name=category_name,
                        weight=category_weight,
                        assignments=assignments
                    )

                    period.categories.append(category)

                section.periods.append(period)

            sections.append(section)

        # Create GradeData model
        grade_data = GradeData(
            timestamp=datetime.now(),
            sections=sections
        )

        return grade_data


def main():
    """Main execution for testing"""
    try:
        fetcher = APIGradeFetcherV2()

        logger.info("Starting API grade fetch (v2)...")
        grade_data = fetcher.fetch_all_grades()

        # Summary
        total_sections = len(grade_data.sections)
        total_assignments = len(grade_data.get_all_assignments())

        logger.info(f"Summary: {total_sections} sections, {total_assignments} assignments")

        # Print sample assignment
        if total_assignments > 0:
            sample = grade_data.get_all_assignments()[0]
            section, period, category, assignment = sample
            logger.info(f"\nSample assignment:")
            logger.info(f"  Section: {section.full_name}")
            logger.info(f"  Period: {period.name}")
            logger.info(f"  Category: {category.name}")
            logger.info(f"  Assignment: {assignment.title}")
            logger.info(f"  Grade: {assignment.grade_string()}")
            logger.info(f"  ID: {assignment.assignment_id}")

    except Exception as e:
        logger.error(f"Error fetching grades: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
