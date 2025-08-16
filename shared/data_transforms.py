"""
Data transformation and validation utilities for grade data.
Provides clean interfaces for data processing and analysis.
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class AssignmentSummary:
    """Summary statistics for an individual assignment."""
    title: str
    grade: str
    due_date: Optional[str]
    category: str
    course: str
    period: str
    numeric_grade: Optional[float]
    is_missing: bool
    is_not_graded: bool
    has_comment: bool


@dataclass
class CourseSummary:
    """Summary statistics for a course."""
    name: str
    course_grade: str
    periods: List[str]
    total_assignments: int
    missing_assignments: int
    not_graded_assignments: int
    average_numeric_grade: Optional[float]
    grade_distribution: Dict[str, int]


@dataclass
class GradeSummary:
    """Overall grade summary across all courses."""
    total_courses: int
    total_assignments: int
    missing_assignments: int
    not_graded_assignments: int
    overall_average: Optional[float]
    courses: List[CourseSummary]
    timestamp: str


class GradeDataTransformer:
    """Handles transformation and analysis of grade data."""
    
    @staticmethod
    def extract_numeric_grade(grade_str: str) -> Optional[float]:
        """
        Extract numeric value from grade string.
        
        Args:
            grade_str: Grade string (e.g., "85%", "B+", "95.5%")
            
        Returns:
            Numeric grade value or None if not extractable
        """
        if not isinstance(grade_str, str):
            return None
        
        # Handle percentage grades
        if '%' in grade_str:
            try:
                return float(grade_str.replace('%', '').strip())
            except ValueError:
                pass
        
        # Handle fraction grades (e.g., "18/20")
        fraction_match = re.match(r'^(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)$', grade_str.strip())
        if fraction_match:
            try:
                numerator = float(fraction_match.group(1))
                denominator = float(fraction_match.group(2))
                if denominator > 0:
                    return (numerator / denominator) * 100
            except ValueError:
                pass
        
        # Handle decimal grades (assume out of 100 if > 4, otherwise out of 4)
        try:
            numeric_value = float(grade_str.strip())
            if 0 <= numeric_value <= 4:
                # Assume 4.0 scale, convert to percentage
                return (numeric_value / 4.0) * 100
            elif 0 <= numeric_value <= 100:
                # Assume percentage
                return numeric_value
        except ValueError:
            pass
        
        # Handle letter grades
        letter_grade_map = {
            'A+': 97, 'A': 93, 'A-': 90,
            'B+': 87, 'B': 83, 'B-': 80,
            'C+': 77, 'C': 73, 'C-': 70,
            'D+': 67, 'D': 63, 'D-': 60,
            'F': 50
        }
        
        grade_upper = grade_str.strip().upper()
        if grade_upper in letter_grade_map:
            return letter_grade_map[grade_upper]
        
        return None
    
    @staticmethod
    def categorize_grade(numeric_grade: float) -> str:
        """
        Categorize numeric grade into letter grade range.
        
        Args:
            numeric_grade: Numeric grade (0-100)
            
        Returns:
            Grade category string
        """
        if numeric_grade >= 90:
            return 'A (90-100%)'
        elif numeric_grade >= 80:
            return 'B (80-89%)'
        elif numeric_grade >= 70:
            return 'C (70-79%)'
        elif numeric_grade >= 60:
            return 'D (60-69%)'
        else:
            return 'F (0-59%)'
    
    @staticmethod
    def extract_all_assignments(grades_data: Dict) -> List[AssignmentSummary]:
        """
        Extract all assignments from grade data into a flat list.
        
        Args:
            grades_data: Hierarchical grade data
            
        Returns:
            List of AssignmentSummary objects
        """
        assignments = []
        
        for course_name, course_data in grades_data.items():
            periods = course_data.get('periods', {})
            course_grade = course_data.get('course_grade', 'N/A')
            
            for period_name, period_data in periods.items():
                categories = period_data.get('categories', {})
                
                for category_name, category_data in categories.items():
                    category_assignments = category_data.get('assignments', [])
                    
                    for assignment in category_assignments:
                        title = assignment.get('title', 'Unknown')
                        grade = assignment.get('grade', 'N/A')
                        due_date = assignment.get('due_date')
                        comment = assignment.get('comment', '')
                        
                        numeric_grade = GradeDataTransformer.extract_numeric_grade(grade)
                        is_missing = grade == 'Missing'
                        is_not_graded = grade == 'Not graded'
                        has_comment = bool(comment.strip())
                        
                        assignment_summary = AssignmentSummary(
                            title=title,
                            grade=grade,
                            due_date=due_date,
                            category=category_name,
                            course=course_name,
                            period=period_name,
                            numeric_grade=numeric_grade,
                            is_missing=is_missing,
                            is_not_graded=is_not_graded,
                            has_comment=has_comment
                        )
                        
                        assignments.append(assignment_summary)
        
        return assignments
    
    @staticmethod
    def create_course_summary(course_name: str, course_data: Dict, assignments: List[AssignmentSummary]) -> CourseSummary:
        """
        Create summary statistics for a single course.
        
        Args:
            course_name: Name of the course
            course_data: Course data from grade structure
            assignments: List of assignments for this course
            
        Returns:
            CourseSummary object
        """
        course_assignments = [a for a in assignments if a.course == course_name]
        
        total_assignments = len(course_assignments)
        missing_assignments = sum(1 for a in course_assignments if a.is_missing)
        not_graded_assignments = sum(1 for a in course_assignments if a.is_not_graded)
        
        # Calculate average of numeric grades
        numeric_grades = [a.numeric_grade for a in course_assignments if a.numeric_grade is not None]
        average_numeric_grade = sum(numeric_grades) / len(numeric_grades) if numeric_grades else None
        
        # Create grade distribution
        grade_distribution = {'A (90-100%)': 0, 'B (80-89%)': 0, 'C (70-79%)': 0, 'D (60-69%)': 0, 'F (0-59%)': 0}
        for grade in numeric_grades:
            category = GradeDataTransformer.categorize_grade(grade)
            grade_distribution[category] += 1
        
        periods = list(course_data.get('periods', {}).keys())
        course_grade = course_data.get('course_grade', 'N/A')
        
        return CourseSummary(
            name=course_name,
            course_grade=course_grade,
            periods=periods,
            total_assignments=total_assignments,
            missing_assignments=missing_assignments,
            not_graded_assignments=not_graded_assignments,
            average_numeric_grade=average_numeric_grade,
            grade_distribution=grade_distribution
        )
    
    @staticmethod
    def create_grade_summary(grades_data: Dict, timestamp: str = None) -> GradeSummary:
        """
        Create comprehensive summary of all grade data.
        
        Args:
            grades_data: Complete grade data structure
            timestamp: Optional timestamp for the summary
            
        Returns:
            GradeSummary object with comprehensive statistics
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Extract all assignments
        all_assignments = GradeDataTransformer.extract_all_assignments(grades_data)
        
        # Calculate overall statistics
        total_courses = len(grades_data)
        total_assignments = len(all_assignments)
        missing_assignments = sum(1 for a in all_assignments if a.is_missing)
        not_graded_assignments = sum(1 for a in all_assignments if a.is_not_graded)
        
        # Calculate overall average
        numeric_grades = [a.numeric_grade for a in all_assignments if a.numeric_grade is not None]
        overall_average = sum(numeric_grades) / len(numeric_grades) if numeric_grades else None
        
        # Create course summaries
        course_summaries = []
        for course_name, course_data in grades_data.items():
            course_summary = GradeDataTransformer.create_course_summary(course_name, course_data, all_assignments)
            course_summaries.append(course_summary)
        
        return GradeSummary(
            total_courses=total_courses,
            total_assignments=total_assignments,
            missing_assignments=missing_assignments,
            not_graded_assignments=not_graded_assignments,
            overall_average=overall_average,
            courses=course_summaries,
            timestamp=timestamp
        )
    
    @staticmethod
    def filter_assignments_by_criteria(
        assignments: List[AssignmentSummary],
        course: Optional[str] = None,
        period: Optional[str] = None,
        category: Optional[str] = None,
        missing_only: bool = False,
        not_graded_only: bool = False,
        with_comments_only: bool = False
    ) -> List[AssignmentSummary]:
        """
        Filter assignments by various criteria.
        
        Args:
            assignments: List of assignments to filter
            course: Filter by course name
            period: Filter by period name
            category: Filter by category name
            missing_only: Only return missing assignments
            not_graded_only: Only return not graded assignments
            with_comments_only: Only return assignments with comments
            
        Returns:
            Filtered list of assignments
        """
        filtered_assignments = assignments
        
        if course:
            filtered_assignments = [a for a in filtered_assignments if a.course == course]
        
        if period:
            filtered_assignments = [a for a in filtered_assignments if a.period == period]
        
        if category:
            filtered_assignments = [a for a in filtered_assignments if a.category == category]
        
        if missing_only:
            filtered_assignments = [a for a in filtered_assignments if a.is_missing]
        
        if not_graded_only:
            filtered_assignments = [a for a in filtered_assignments if a.is_not_graded]
        
        if with_comments_only:
            filtered_assignments = [a for a in filtered_assignments if a.has_comment]
        
        return filtered_assignments
    
    @staticmethod
    def compare_snapshots(current_data: Dict, previous_data: Dict) -> Dict[str, Any]:
        """
        Compare two grade snapshots and identify changes.
        
        Args:
            current_data: Current grade data
            previous_data: Previous grade data
            
        Returns:
            Dictionary containing change analysis
        """
        current_assignments = GradeDataTransformer.extract_all_assignments(current_data)
        previous_assignments = GradeDataTransformer.extract_all_assignments(previous_data)
        
        # Create lookup dictionaries
        current_lookup = {f"{a.course}|{a.period}|{a.category}|{a.title}": a for a in current_assignments}
        previous_lookup = {f"{a.course}|{a.period}|{a.category}|{a.title}": a for a in previous_assignments}
        
        # Find changes
        new_assignments = []
        grade_changes = []
        removed_assignments = []
        
        # Check for new and changed assignments
        for key, current_assignment in current_lookup.items():
            if key not in previous_lookup:
                new_assignments.append(current_assignment)
            else:
                previous_assignment = previous_lookup[key]
                if current_assignment.grade != previous_assignment.grade:
                    grade_changes.append({
                        'assignment': current_assignment,
                        'old_grade': previous_assignment.grade,
                        'new_grade': current_assignment.grade
                    })
        
        # Check for removed assignments
        for key, previous_assignment in previous_lookup.items():
            if key not in current_lookup:
                removed_assignments.append(previous_assignment)
        
        return {
            'new_assignments': new_assignments,
            'grade_changes': grade_changes,
            'removed_assignments': removed_assignments,
            'total_changes': len(new_assignments) + len(grade_changes) + len(removed_assignments)
        }


class GradeDataValidator:
    """Validates grade data structure and content."""
    
    @staticmethod
    def validate_structure(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate the basic structure of grade data.
        
        Args:
            data: Grade data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Grade data must be a dictionary")
            return False, errors
        
        if not data:
            errors.append("Grade data cannot be empty")
            return False, errors
        
        for course_name, course_data in data.items():
            if not isinstance(course_data, dict):
                errors.append(f"Course '{course_name}' data must be a dictionary")
                continue
            
            if 'periods' not in course_data:
                errors.append(f"Course '{course_name}' missing 'periods' key")
                continue
            
            periods = course_data['periods']
            if not isinstance(periods, dict):
                errors.append(f"Course '{course_name}' periods must be a dictionary")
                continue
            
            for period_name, period_data in periods.items():
                if not isinstance(period_data, dict):
                    errors.append(f"Period '{period_name}' in course '{course_name}' must be a dictionary")
                    continue
                
                if 'categories' not in period_data:
                    errors.append(f"Period '{period_name}' in course '{course_name}' missing 'categories' key")
                    continue
                
                categories = period_data['categories']
                if not isinstance(categories, dict):
                    errors.append(f"Categories in period '{period_name}' of course '{course_name}' must be a dictionary")
                    continue
                
                for category_name, category_data in categories.items():
                    if not isinstance(category_data, dict):
                        errors.append(f"Category '{category_name}' data must be a dictionary")
                        continue
                    
                    if 'assignments' not in category_data:
                        errors.append(f"Category '{category_name}' missing 'assignments' key")
                        continue
                    
                    assignments = category_data['assignments']
                    if not isinstance(assignments, list):
                        errors.append(f"Assignments in category '{category_name}' must be a list")
                        continue
                    
                    for i, assignment in enumerate(assignments):
                        if not isinstance(assignment, dict):
                            errors.append(f"Assignment {i} in category '{category_name}' must be a dictionary")
                            continue
                        
                        required_fields = ['title', 'grade']
                        for field in required_fields:
                            if field not in assignment:
                                errors.append(f"Assignment {i} in category '{category_name}' missing required field '{field}'")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def validate_content(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate the content quality of grade data.
        
        Args:
            data: Grade data to validate
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        all_assignments = GradeDataTransformer.extract_all_assignments(data)
        
        # Check for suspicious patterns
        total_assignments = len(all_assignments)
        if total_assignments == 0:
            warnings.append("No assignments found in data")
        
        missing_count = sum(1 for a in all_assignments if a.is_missing)
        if missing_count > total_assignments * 0.5:
            warnings.append(f"High number of missing assignments: {missing_count}/{total_assignments}")
        
        not_graded_count = sum(1 for a in all_assignments if a.is_not_graded)
        if not_graded_count > total_assignments * 0.3:
            warnings.append(f"High number of not graded assignments: {not_graded_count}/{total_assignments}")
        
        # Check for assignments without titles
        no_title_count = sum(1 for a in all_assignments if not a.title or a.title.strip() == 'Unknown')
        if no_title_count > 0:
            warnings.append(f"Found {no_title_count} assignments without proper titles")
        
        # Check for suspicious grade patterns
        numeric_grades = [a.numeric_grade for a in all_assignments if a.numeric_grade is not None]
        if numeric_grades:
            avg_grade = sum(numeric_grades) / len(numeric_grades)
            if avg_grade > 98:
                warnings.append(f"Suspiciously high average grade: {avg_grade:.1f}%")
            elif avg_grade < 60:
                warnings.append(f"Suspiciously low average grade: {avg_grade:.1f}%")
        
        is_valid = len(warnings) == 0
        return is_valid, warnings


if __name__ == "__main__":
    # Test the transformer with sample data
    sample_data = {
        "Math 101": {
            "course_grade": "85%",
            "periods": {
                "Period 1": {
                    "period_grade": "85%",
                    "categories": {
                        "Tests": {
                            "category_grade": "80%",
                            "assignments": [
                                {"title": "Test 1", "grade": "85%", "due_date": "2024-01-15"},
                                {"title": "Test 2", "grade": "75%", "due_date": "2024-02-15"}
                            ]
                        }
                    }
                }
            }
        }
    }
    
    # Test validation
    is_valid, errors = GradeDataValidator.validate_structure(sample_data)
    print(f"Structure validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
    
    # Test transformation
    assignments = GradeDataTransformer.extract_all_assignments(sample_data)
    print(f"Extracted {len(assignments)} assignments")
    
    summary = GradeDataTransformer.create_grade_summary(sample_data)
    print(f"Summary: {summary.total_courses} courses, {summary.total_assignments} assignments")