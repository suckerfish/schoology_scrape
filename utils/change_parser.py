"""
Change parsing and formatting utilities for grade change detection.

This module provides functions to parse, format, and enhance grade change data
for display in the Streamlit dashboard.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


def parse_change_line(change_line: str, snapshot_data: Optional[Dict] = None) -> Optional[Dict]:
    """
    Parse a single change line into structured data with assignment name extraction.

    Args:
        change_line: Raw change line from grade_changes.log
        snapshot_data: Optional snapshot data to look up assignment names

    Returns:
        Dictionary with parsed change data including assignment name, or None if parsing fails
    """
    if '→' not in change_line:
        return None

    # Split by the arrow to get old and new values
    arrow_parts = change_line.split('→')
    if len(arrow_parts) != 2:
        return None

    # The left side contains path and old value
    left_side = arrow_parts[0].strip()
    new_value = arrow_parts[1].strip()

    # Split left side into path and old value (last colon before arrow)
    last_colon = left_side.rfind(':')
    if last_colon == -1:
        return None

    path_part = left_side[:last_colon].strip()
    old_value = left_side[last_colon + 1:].strip()

    # Extract course name (first item in root)
    course_match = re.search(r"root\['([^']+)'\]", path_part)
    course = course_match.group(1) if course_match else "Unknown"

    # Shorten course name for display
    course = course.replace(': Section ', ' Sec ')

    # Extract period if present
    period_match = re.search(r"\['periods'\]\['([^']+)'\]", path_part)
    period = period_match.group(1) if period_match else ""

    # Extract category if present
    category_match = re.search(r"\['categories'\]\['([^']+)'\]", path_part)
    category = category_match.group(1) if category_match else ""

    # Shorten category name
    if category:
        # Remove percentage info for cleaner display
        category = re.sub(r'\s*\(\d+%\)', '', category)

    # Extract assignment index if present
    assignment_idx_match = re.search(r"\['assignments'\]\[(\d+)\]", path_part)
    assignment_idx = assignment_idx_match.group(1) if assignment_idx_match else None

    # Extract assignment name from path or snapshot data
    assignment_name = None
    if assignment_idx is not None:
        # Try to extract from the change line itself if it's a title change
        if "'title']" in path_part:
            assignment_name = new_value.strip("'\"")
        # Otherwise try to look it up from snapshot data
        elif snapshot_data:
            assignment_name = _lookup_assignment_name(
                snapshot_data, course, period, category, int(assignment_idx)
            )

    # Determine field type
    if "'grade'" in path_part:
        if "'period_grade'" in path_part:
            field_type = "Period Grade"
        elif "'course_grade'" in path_part:
            field_type = "Course Grade"
        elif "'category_grade'" in path_part:
            field_type = "Category Grade"
        else:
            field_type = "Grade"
    elif "'due_date'" in path_part:
        field_type = "Due Date"
    elif "'comment'" in path_part:
        field_type = "Comment"
    elif "'title'" in path_part:
        field_type = "Title"
    else:
        field_type = "Other"

    # Clean up category display
    display_category = category if category else period if period else "—"

    return {
        'course': course,
        'period': period,
        'category': display_category,
        'assignment': assignment_name or "—",
        'field': field_type,
        'assignment_idx': assignment_idx,
        'old_value': old_value,
        'new_value': new_value,
        'raw': change_line
    }


def _lookup_assignment_name(snapshot_data: Dict, course: str, period: str,
                            category: str, assignment_idx: int) -> Optional[str]:
    """
    Look up assignment name from snapshot data.

    Args:
        snapshot_data: Full snapshot data structure
        course: Course name (may be shortened)
        period: Period name
        category: Category name (may be shortened)
        assignment_idx: Assignment array index

    Returns:
        Assignment title if found, None otherwise
    """
    try:
        # Find matching course (handle shortened names)
        course_data = None
        for course_key in snapshot_data.keys():
            if course in course_key or course_key.replace(': Section ', ' Sec ') == course:
                course_data = snapshot_data[course_key]
                break

        if not course_data:
            return None

        # Navigate to assignment
        periods = course_data.get('periods', {})
        if period and period in periods:
            period_data = periods[period]
            categories = period_data.get('categories', {})

            # Find matching category (handle shortened names)
            category_data = None
            for cat_key in categories.keys():
                clean_cat = re.sub(r'\s*\(\d+%\)', '', cat_key)
                if category == clean_cat or category in cat_key:
                    category_data = categories[cat_key]
                    break

            if category_data:
                assignments = category_data.get('assignments', [])
                if 0 <= assignment_idx < len(assignments):
                    return assignments[assignment_idx].get('title')

        return None
    except Exception:
        return None


def calculate_grade_delta(old_value: str, new_value: str) -> Optional[Dict[str, Any]]:
    """
    Calculate the delta for a grade change.

    Args:
        old_value: Old grade value
        new_value: New grade value

    Returns:
        Dict with delta info: {'numeric_delta': float, 'direction': 'up'|'down'|'new',
                               'percentage': float, 'display': str}
        Returns None if values can't be compared
    """
    # Handle "Not graded" cases
    if 'not graded' in old_value.lower():
        # New grade - extract score
        score_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', new_value)
        if score_match:
            earned = float(score_match.group(1))
            total = float(score_match.group(2))
            percentage = (earned / total * 100) if total > 0 else 0
            return {
                'numeric_delta': earned,
                'direction': 'new',
                'percentage': percentage,
                'display': f'New: {percentage:.1f}%'
            }
        return None

    # Parse fraction grades (e.g., "18 / 20")
    old_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', old_value)
    new_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', new_value)

    if old_match and new_match:
        old_earned = float(old_match.group(1))
        old_total = float(old_match.group(2))
        new_earned = float(new_match.group(1))
        new_total = float(new_match.group(2))

        old_pct = (old_earned / old_total * 100) if old_total > 0 else 0
        new_pct = (new_earned / new_total * 100) if new_total > 0 else 0

        delta = new_pct - old_pct
        direction = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

        return {
            'numeric_delta': delta,
            'direction': direction,
            'percentage': new_pct,
            'display': f'{delta:+.1f}%' if direction != 'same' else '—'
        }

    return None


def get_grade_style(old_value: str, new_value: str, field_type: str) -> Dict[str, str]:
    """
    Get styling for a grade change row.

    Args:
        old_value: Old value
        new_value: New value
        field_type: Type of field (Grade, Due Date, etc.)

    Returns:
        Dict with CSS style properties
    """
    # Only style grade changes
    if field_type not in ['Grade', 'Period Grade', 'Course Grade', 'Category Grade']:
        return {}

    delta = calculate_grade_delta(old_value, new_value)

    if not delta:
        return {}

    # Color coding based on direction
    if delta['direction'] == 'new':
        # New grade - blue background
        return {'background-color': '#E3F2FD'}  # Light blue
    elif delta['direction'] == 'up':
        # Improvement - green background
        return {'background-color': '#E8F5E9'}  # Light green
    elif delta['direction'] == 'down':
        # Decline - yellow background
        return {'background-color': '#FFF9C4'}  # Light yellow

    return {}


def parse_detailed_message(formatted_message: str, snapshot_data: Optional[Dict] = None) -> Optional[Dict]:
    """
    Parse the formatted message to extract structured changes.

    Args:
        formatted_message: The formatted change message
        snapshot_data: Optional snapshot data for assignment name lookup

    Returns:
        Dict with summary, raw_changes, and parsed_changes
    """
    if not formatted_message:
        return None

    # Split the message into parts
    parts = formatted_message.split('\n\nDetailed changes:\n')
    if len(parts) < 2:
        return None

    summary = parts[0]
    changes_text = parts[1]

    # Extract individual changes (each starts with a bullet point)
    raw_changes = []
    parsed_changes = []

    for line in changes_text.split('\n'):
        line = line.strip()
        if line.startswith('•'):
            change_text = line[2:]  # Remove bullet point
            raw_changes.append(change_text)

            # Parse into structured format
            parsed = parse_change_line(change_text, snapshot_data)
            if parsed:
                # Add delta information for grades
                if parsed['field'] in ['Grade', 'Period Grade', 'Course Grade', 'Category Grade']:
                    delta = calculate_grade_delta(parsed['old_value'], parsed['new_value'])
                    parsed['delta'] = delta
                parsed_changes.append(parsed)

    return {
        'summary': summary,
        'raw_changes': raw_changes,
        'parsed_changes': parsed_changes
    }


def load_snapshot_for_timestamp(timestamp: str) -> Optional[Dict]:
    """
    Load the snapshot data file closest to the given timestamp.

    Args:
        timestamp: ISO format timestamp

    Returns:
        Snapshot data dict, or None if not found
    """
    from datetime import datetime

    data_dir = Path("data")
    if not data_dir.exists():
        return None

    # Parse target timestamp
    try:
        target_dt = datetime.fromisoformat(timestamp)
    except:
        return None

    # Find snapshot files
    snapshot_files = list(data_dir.glob("all_courses_data_*.json"))
    if not snapshot_files:
        return None

    # Find closest snapshot
    closest_file = None
    min_diff = None

    for file_path in snapshot_files:
        # Extract timestamp from filename: all_courses_data_YYYYMMDD_HHMMSS.json
        match = re.search(r'all_courses_data_(\d{8})_(\d{6})\.json', file_path.name)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            try:
                file_dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                diff = abs((file_dt - target_dt).total_seconds())

                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    closest_file = file_path
            except:
                continue

    # Load the closest snapshot
    if closest_file:
        try:
            with open(closest_file, 'r') as f:
                return json.load(f)
        except:
            pass

    return None
