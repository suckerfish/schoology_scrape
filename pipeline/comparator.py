import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from deepdiff import DeepDiff
from shared.config import get_config
from shared.diff_logger import DiffLogger

class GradeComparator:
    """Handles change detection logic using DeepDiff"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        self.diff_logger = DiffLogger(self.config)

    def detect_changes_from_file(self, new_data: Dict[str, Any], grade_changes_only: bool = False) -> Optional[Dict[str, Any]]:
        """
        Compare new data with the latest local file to detect changes

        Args:
            new_data: New grade data to compare
            grade_changes_only: If True, only report grade-related changes

        Returns:
            Dict containing change information, or None if no changes
        """
        try:
            # Find the latest local file
            data_dir = Path('data')
            if not data_dir.exists():
                self.logger.info("No data directory found - treating as initial data")
                return {
                    'type': 'initial',
                    'message': 'Initial grade data captured (no local files)',
                    'data': new_data
                }

            latest_files = sorted(data_dir.glob('all_courses_data_*.json'))
            if not latest_files:
                self.logger.info("No previous files found - treating as initial data")
                return {
                    'type': 'initial',
                    'message': 'Initial grade data captured (no previous files)',
                    'data': new_data
                }

            latest_file = latest_files[-1]

            # Load the latest file data
            with open(latest_file, 'r') as f:
                latest_data = json.load(f)

            # Perform deep comparison
            diff = DeepDiff(latest_data, new_data, ignore_order=True)

            if diff:
                self.logger.info(f"Changes detected compared to {latest_file}")
                changes = self._process_changes(diff, latest_data, new_data, grade_changes_only=grade_changes_only)
                # Add comparison file info for logging
                changes['comparison_files'] = [str(latest_file)]

                # If filtering for grade changes only, check if any grade changes were found
                if grade_changes_only and not changes.get('detailed_changes'):
                    self.logger.info("No grade changes detected (only non-grade changes found)")
                    return None

                return changes
            else:
                self.logger.info("No changes detected compared to latest file")
                return None

        except Exception as e:
            self.logger.error(f"Error detecting changes from file: {e}")
            return None
    
    def _process_changes(self, diff: DeepDiff, old_data: Dict[str, Any], new_data: Dict[str, Any], grade_changes_only: bool = False) -> Dict[str, Any]:
        """
        Process DeepDiff output into a structured change report

        Args:
            diff: DeepDiff result
            old_data: Previous data
            new_data: New data
            grade_changes_only: If True, only include grade-related changes

        Returns:
            Dict containing processed change information
        """
        detailed_changes = self._extract_detailed_changes(diff, grade_changes_only=grade_changes_only, new_data=new_data)

        changes = {
            'type': 'update',
            'summary': self._generate_change_summary(diff),
            'detailed_changes': detailed_changes,
            'diff_raw': diff,
            'old_data': old_data,
            'new_data': new_data,
            'grade_changes_only': grade_changes_only
        }

        # Log raw diff for debugging (if enabled)
        self.diff_logger.log_raw_diff(
            raw_diff=diff,
            detailed_changes=detailed_changes,
            old_data_summary=self._summarize_data(old_data),
            new_data_summary=self._summarize_data(new_data),
            comparison_files=changes.get('comparison_files', [])
        )

        return changes
    
    def _generate_change_summary(self, diff: DeepDiff) -> str:
        """Generate a human-readable summary of changes"""
        summary_parts = []
        
        if 'values_changed' in diff:
            summary_parts.append(f"{len(diff['values_changed'])} value(s) changed")
        
        if 'dictionary_item_added' in diff:
            summary_parts.append(f"{len(diff['dictionary_item_added'])} item(s) added")
        
        if 'dictionary_item_removed' in diff:
            summary_parts.append(f"{len(diff['dictionary_item_removed'])} item(s) removed")
        
        if 'iterable_item_added' in diff:
            summary_parts.append(f"{len(diff['iterable_item_added'])} list item(s) added")
        
        if 'iterable_item_removed' in diff:
            summary_parts.append(f"{len(diff['iterable_item_removed'])} list item(s) removed")
        
        if not summary_parts:
            return "Unknown changes detected"
        
        return ", ".join(summary_parts)

    def _is_grade_change(self, path: str) -> bool:
        """
        Check if a DeepDiff path represents a grade-related change.

        Args:
            path: DeepDiff path string (e.g., "root['Course']['periods']['T1']['categories']['Tests']['assignments'][0]['grade']")

        Returns:
            True if the path represents a grade change, False otherwise

        Grade-related paths include:
            - Assignment grades: ['grade']
            - Exception status: ['exception'] (Missing/Excused/Incomplete)
            - Teacher comments: ['comment']
            - Max points: ['max_points']
            - Aggregate grades: ['course_grade'], ['period_grade'], ['category_grade']
        """
        # Grade value fields
        if "['grade']" in path:
            return True

        # Exception status (Missing/Excused/Incomplete)
        if "['exception']" in path:
            return True

        # Teacher comments on grades
        if "['comment']" in path:
            return True

        # Max points changes affect grade calculations
        if "['max_points']" in path:
            return True

        # Aggregate grade fields
        if any(grade_field in path for grade_field in ["['course_grade']", "['period_grade']", "['category_grade']"]):
            return True

        return False

    def _is_new_graded_assignment(self, path: str, new_data: Dict[str, Any]) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if an added item is a new assignment with a grade.

        Args:
            path: DeepDiff path string for the added item
            new_data: The new data containing the added item

        Returns:
            Tuple of (is_graded_assignment, assignment_data)
            - is_graded_assignment: True if this is an assignment with a grade
            - assignment_data: The assignment dict if found, None otherwise
        """
        # Check if path points to an assignment in the assignments list
        if "['assignments']" not in path:
            return False, None

        try:
            # Parse the path to extract the assignment data
            # Path format: "root['Course']['periods']['Period']['categories']['Category']['assignments'][index]"
            # Remove 'root' prefix
            path_clean = path.replace('root', '')

            # Navigate through the data structure using the path
            current = new_data
            # Split by '][' to get path components, handle both ['key'] and [index] formats
            import re
            # Extract all keys/indices between brackets
            keys = re.findall(r"\['([^']+)'\]|\[(\d+)\]", path_clean)

            for key_match in keys:
                key = key_match[0] if key_match[0] else int(key_match[1])
                if isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list):
                    if isinstance(key, int) and key < len(current):
                        current = current[key]
                    else:
                        return False, None
                else:
                    return False, None

                if current is None:
                    return False, None

            # Check if this is an assignment dict with a grade
            if isinstance(current, dict) and 'grade' in current:
                grade = current.get('grade', 'Not graded')
                # Consider it a graded assignment if it has any grade other than "Not graded"
                if grade and grade != 'Not graded':
                    return True, current

            return False, None

        except Exception as e:
            self.logger.debug(f"Error checking if item is graded assignment: {e}")
            return False, None

    def _find_graded_assignments_in_added_dict(self, path: str, new_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively search an added dictionary (like a new period or category) for graded assignments.

        Args:
            path: DeepDiff path to the added dictionary item
            new_data: The new data containing the added item

        Returns:
            List of change dictionaries for graded assignments found
        """
        graded_assignments = []

        try:
            # Parse the path to get to the added dictionary
            path_clean = path.replace('root', '')
            current = new_data

            import re
            keys = re.findall(r"\['([^']+)'\]|\[(\d+)\]", path_clean)

            for key_match in keys:
                key = key_match[0] if key_match[0] else int(key_match[1])
                if isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list):
                    if isinstance(key, int) and key < len(current):
                        current = current[key]
                    else:
                        return graded_assignments
                else:
                    return graded_assignments

                if current is None:
                    return graded_assignments

            # Now recursively search current for assignments with grades
            def search_for_graded_assignments(obj, current_path):
                if isinstance(obj, dict):
                    # Check if this is an assignment with a grade
                    if 'title' in obj and 'grade' in obj:
                        grade = obj.get('grade', 'Not graded')
                        if grade and grade != 'Not graded':
                            graded_assignments.append({
                                'type': 'new_graded_assignment',
                                'path': current_path,
                                'assignment_data': obj
                            })
                    # Recursively search nested dictionaries
                    for key, value in obj.items():
                        search_for_graded_assignments(value, f"{current_path}['{key}']")
                elif isinstance(obj, list):
                    # Recursively search list items
                    for idx, item in enumerate(obj):
                        search_for_graded_assignments(item, f"{current_path}[{idx}]")

            search_for_graded_assignments(current, path)

        except Exception as e:
            self.logger.debug(f"Error searching for graded assignments in added dict: {e}")

        return graded_assignments

    def _extract_detailed_changes(self, diff: DeepDiff, grade_changes_only: bool = False, new_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract detailed change information for notifications

        Args:
            diff: DeepDiff result object
            grade_changes_only: If True, only include grade-related changes
            new_data: The new data for checking new graded assignments

        Returns:
            List of change dictionaries
        """
        detailed_changes = []

        # Process value changes
        if 'values_changed' in diff:
            for path, change in diff['values_changed'].items():
                # Filter non-grade changes if requested
                if grade_changes_only and not self._is_grade_change(path):
                    continue

                detailed_changes.append({
                    'type': 'value_changed',
                    'path': path,
                    'old_value': change['old_value'],
                    'new_value': change['new_value']
                })

        # When filtering for grade changes, still check for new graded assignments
        if grade_changes_only and new_data:
            # Process new assignments that have grades (from list additions)
            if 'iterable_item_added' in diff:
                for path in diff['iterable_item_added']:
                    is_graded, assignment_data = self._is_new_graded_assignment(path, new_data)
                    if is_graded and assignment_data:
                        detailed_changes.append({
                            'type': 'new_graded_assignment',
                            'path': path,
                            'assignment_data': assignment_data
                        })

            # Also check dictionary additions (like new periods/categories) for graded assignments within them
            if 'dictionary_item_added' in diff:
                for path in diff['dictionary_item_added']:
                    # Recursively search for graded assignments within added dictionaries
                    added_items = self._find_graded_assignments_in_added_dict(path, new_data)
                    detailed_changes.extend(added_items)

        # Include all additions/removals if not filtering for grade changes
        if not grade_changes_only:
            # Process additions
            if 'dictionary_item_added' in diff:
                for path in diff['dictionary_item_added']:
                    detailed_changes.append({
                        'type': 'item_added',
                        'path': path,
                        'value': 'New item added'  # Don't try to extract value from set
                    })

            # Process removals
            if 'dictionary_item_removed' in diff:
                for path in diff['dictionary_item_removed']:
                    detailed_changes.append({
                        'type': 'item_removed',
                        'path': path,
                        'value': 'Item removed'  # Don't try to extract value from set
                    })

        return detailed_changes
    
    def format_changes_for_notification(self, changes: Dict[str, Any]) -> str:
        """
        Format changes into a human-readable notification message

        Args:
            changes: Change information from detect_changes

        Returns:
            Formatted message string
        """
        if changes['type'] == 'initial':
            return changes['message']

        message = f"Changes detected: {changes['summary']}\n\n"

        # Add detailed changes
        detailed_changes = changes.get('detailed_changes', [])
        if detailed_changes:
            message += "Detailed changes:\n"
            for change in detailed_changes[:10]:  # Limit to first 10 changes
                if change['type'] == 'value_changed':
                    message += f"• {change['path']}: {change['old_value']} → {change['new_value']}\n"
                elif change['type'] == 'new_graded_assignment':
                    # Format new graded assignment with key details
                    assignment = change['assignment_data']
                    title = assignment.get('title', 'Unknown')
                    grade = assignment.get('grade', 'Unknown')
                    message += f"• New assignment with grade: {change['path']}\n"
                    message += f"  Title: {title}\n"
                    message += f"  Grade: {grade}\n"
                elif change['type'] == 'item_added':
                    message += f"• Added: {change['path']} = {change['value']}\n"
                elif change['type'] == 'item_removed':
                    message += f"• Removed: {change['path']} = {change['value']}\n"

            if len(detailed_changes) > 10:
                message += f"• ... and {len(detailed_changes) - 10} more changes\n"

        return message

    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of grade data for logging context.

        Args:
            data: Grade data to summarize

        Returns:
            Dict containing data summary
        """
        if not data:
            return {"total_courses": 0, "total_assignments": 0}

        try:
            total_courses = len(data)
            total_assignments = 0
            course_names = []

            for course_name, course_data in data.items():
                course_names.append(course_name)
                if isinstance(course_data, dict) and 'periods' in course_data:
                    for period_name, period_data in course_data['periods'].items():
                        if isinstance(period_data, dict) and 'categories' in period_data:
                            for category_name, category_data in period_data['categories'].items():
                                if isinstance(category_data, dict) and 'assignments' in category_data:
                                    assignments = category_data['assignments']
                                    if isinstance(assignments, list):
                                        total_assignments += len(assignments)

            return {
                "total_courses": total_courses,
                "total_assignments": total_assignments,
                "course_names": course_names[:5],  # First 5 course names for context
                "has_more_courses": total_courses > 5
            }
        except Exception as e:
            return {
                "error": f"Failed to summarize data: {e}",
                "total_courses": len(data) if isinstance(data, dict) else 0,
                "total_assignments": 0
            }