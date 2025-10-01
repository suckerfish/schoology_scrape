#!/usr/bin/env python3
"""
Fetch grade data from Schoology API in format matching scraper output
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict
from api.client import SchoologyAPIClient


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class APIGradeFetcher:
    """Fetches and structures grade data from API to match scraper format"""

    def __init__(self):
        self.client = SchoologyAPIClient()
        self.sections_cache = {}
        self.categories_cache = {}
        self.assignments_cache = {}
        self.enrollment_id_map = {}  # Maps grade_section_id -> enrollment_section_id

    def _format_grade(self, grade_obj: Dict[str, Any]) -> str:
        """Format grade value to match scraper format (e.g., '5 / 5', 'Missing')"""
        grade = grade_obj.get('grade')
        max_points = grade_obj.get('max_points')

        if grade is None or grade == '':
            return 'Not graded'

        if max_points:
            return f"{grade} / {max_points}"

        return str(grade)

    def _format_timestamp(self, timestamp: int) -> str:
        """Convert Unix timestamp to readable date"""
        if not timestamp:
            return None

        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%m/%d/%y %I:%M%p').lower()

    def _get_assignment_comment(self, section_id: str, assignment_id: str, grade_obj: Dict[str, Any]) -> str:
        """
        Get comment for assignment

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
        """Get assignment title from cache or API, trying enrollment ID first"""
        cache_key = f"{grade_section_id}:{assignment_id}"

        if cache_key not in self.assignments_cache:
            # Try enrollment ID first (may have better permissions)
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

    def _get_assignment_due_date(self, section_id: str, assignment_id: str) -> str:
        """Get assignment due date"""
        cache_key = f"{section_id}:{assignment_id}"

        if cache_key in self.assignments_cache:
            assignment = self.assignments_cache[cache_key]
            due_date = assignment.get('due', '')
            if due_date:
                # Convert from API format (YYYY-MM-DD HH:MM:SS) to scraper format (M/D/YY h:MMpm)
                try:
                    dt = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
                    return dt.strftime('%m/%d/%y %I:%M%p').lower()
                except:
                    return due_date

        return None

    def _get_category_name(self, grade_section_id: str, category_id: int) -> str:
        """Get category name from ID, trying enrollment ID first"""
        if grade_section_id not in self.categories_cache:
            # Try enrollment ID first
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
        title = category.get('title', f'Category {category_id}')
        weight = category.get('weight')

        if weight:
            return f"{title} ({weight}%)"

        return title

    def fetch_all_grades(self) -> Dict[str, Any]:
        """
        Fetch all grade data and structure to match scraper output

        Returns:
            Dict matching scraper format with courses, periods, categories, assignments
        """
        logger.info("Fetching sections...")
        sections = self.client.get_sections()

        logger.info(f"Found {len(sections)} sections")

        # Get all grades at once
        logger.info("Fetching all grades...")
        all_grades = self.client.get_grades()

        # Structure data to match scraper format
        result = {}

        # Build mapping of section IDs (grades API may use different IDs than sections list)
        section_map = {}
        for section in sections:
            enrollment_id = section['id']
            course_title = section.get('course_title', 'Unknown Course')
            section_title = section.get('section_title', '')
            course_key = f"{course_title}: {section_title}" if section_title else course_title
            section_map[enrollment_id] = {
                'course_key': course_key,
                'section_title': section_title,
                'course_title': course_title,
                'enrollment_id': enrollment_id
            }

        # Process grades (using the section IDs from grades API)
        for section_grades in all_grades.get('section', []):
            grade_section_id = section_grades['section_id']

            # Try to find matching section info
            section_info = section_map.get(grade_section_id)
            matched_enrollment_id = None

            if not section_info:
                # Section ID mismatch - try to match by course code or nearby ID
                logger.warning(f"Section ID {grade_section_id} not in sections list, trying to match...")

                # Check if it's off-by-one (known Schoology API quirk)
                for offset in [-1, 1, -2, 2]:
                    nearby_id = str(int(grade_section_id) + offset)
                    if nearby_id in section_map:
                        logger.info(f"  Matched {grade_section_id} to {nearby_id} (offset {offset})")
                        section_info = section_map[nearby_id]
                        matched_enrollment_id = nearby_id
                        break

            if not section_info:
                # Still no match - use generic name
                logger.warning(f"  Could not match section {grade_section_id}, using generic name")
                section_info = {
                    'course_key': f'Unknown Course (Section {grade_section_id})',
                    'section_title': grade_section_id,
                    'course_title': 'Unknown',
                    'enrollment_id': grade_section_id
                }
                matched_enrollment_id = grade_section_id
            elif matched_enrollment_id is None:
                # Direct match
                matched_enrollment_id = section_info.get('enrollment_id', grade_section_id)

            # Store mapping for use in detail fetches
            self.enrollment_id_map[grade_section_id] = matched_enrollment_id

            course_key = section_info['course_key']
            logger.info(f"Processing {course_key}... (grade_id={grade_section_id}, enrollment_id={matched_enrollment_id})")

            # Use the grade section ID for the main loop
            section_id = grade_section_id

            # Initialize course structure
            course_data = {
                'course_grade': 'Not graded',  # Would need calculation
                'periods': {}
            }

            # Process each grading period
            for period in section_grades.get('period', []):
                period_title = period.get('period_title', 'Unknown Period')
                period_data = {
                    'period_grade': 'Not graded',  # Would need calculation
                    'categories': {}
                }

                # Group assignments by category
                category_assignments = defaultdict(list)

                for assignment_grade in period.get('assignment', []):
                    assignment_id = str(assignment_grade['assignment_id'])
                    category_id = assignment_grade.get('category_id')

                    # Get assignment details
                    title = self._get_assignment_title(section_id, assignment_id)
                    grade = self._format_grade(assignment_grade)
                    comment = self._get_assignment_comment(section_id, assignment_id, assignment_grade)
                    due_date = self._get_assignment_due_date(section_id, assignment_id)

                    assignment_dict = {
                        'title': title,
                        'grade': grade,
                        'comment': comment
                    }

                    if due_date:
                        assignment_dict['due_date'] = due_date

                    # Add to appropriate category
                    if category_id:
                        category_name = self._get_category_name(section_id, category_id)
                        category_assignments[category_name].append(assignment_dict)
                    else:
                        # No category - use "Uncategorized"
                        category_assignments['Uncategorized'].append(assignment_dict)

                # Build category structure
                for category_name, assignments in category_assignments.items():
                    period_data['categories'][category_name] = {
                        'assignments': assignments,
                        'category_grade': 'Not calculated'  # Would need calculation
                    }

                course_data['periods'][period_title] = period_data

            result[course_key] = course_data

        return result


def main():
    """Main execution"""
    try:
        fetcher = APIGradeFetcher()

        logger.info("Starting API grade fetch...")
        data = fetcher.fetch_all_grades()

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Get absolute path to data directory
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(script_dir), 'data')
        output_file = os.path.join(data_dir, f'api_grades_{timestamp}.json')

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved API grades to {output_file}")

        # Summary
        total_courses = len(data)
        total_assignments = sum(
            len(cat['assignments'])
            for course in data.values()
            for period in course.get('periods', {}).values()
            for cat in period.get('categories', {}).values()
        )

        logger.info(f"Summary: {total_courses} courses, {total_assignments} assignments")

    except Exception as e:
        logger.error(f"Error fetching grades: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
