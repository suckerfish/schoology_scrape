"""
Pydantic models for normalized grade data with unique identifiers.

This module defines the data structures for ID-based change detection,
replacing the old string-key-based nested dictionaries with proper models
that preserve unique identifiers from the Schoology API.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class Assignment(BaseModel):
    """
    Normalized assignment model with stable unique identifier.

    Attributes:
        assignment_id: Unique identifier from Schoology API
        title: Assignment title
        earned_points: Points earned (None if not graded)
        max_points: Maximum points possible (None if not graded)
        exception: Exception status (Missing, Excused, Incomplete, None)
        comment: Teacher comment
        due_date: Due date as datetime (None if no due date)
    """
    assignment_id: str
    title: str
    earned_points: Optional[Decimal] = None
    max_points: Optional[Decimal] = None
    exception: Optional[str] = None  # "Missing", "Excused", "Incomplete"
    comment: str = "No comment"
    due_date: Optional[datetime] = None

    @field_validator('earned_points', 'max_points', mode='before')
    @classmethod
    def parse_decimal(cls, v):
        """Convert various numeric formats to Decimal"""
        if v is None or v == '':
            return None
        try:
            return Decimal(str(v))
        except:
            return None

    @field_validator('due_date', mode='before')
    @classmethod
    def parse_due_date(cls, v):
        """Parse various date formats to datetime"""
        if v is None or v == '':
            return None

        if isinstance(v, datetime):
            return v

        # Try parsing common formats
        formats = [
            '%m/%d/%y %I:%M%p',  # 08/15/25 03:00pm
            '%Y-%m-%d %H:%M:%S',  # 2025-08-15 15:00:00
            '%Y-%m-%dT%H:%M:%S',  # 2025-08-15T15:00:00
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(v), fmt)
            except:
                continue

        return None

    def has_grade(self) -> bool:
        """Check if assignment has a grade"""
        return (self.exception is not None) or (self.earned_points is not None)

    def grade_string(self) -> str:
        """Format grade as human-readable string"""
        if self.exception:
            return self.exception

        if self.earned_points is None:
            return "Not graded"

        if self.max_points:
            return f"{self.earned_points} / {self.max_points}"

        return str(self.earned_points)

    def grade_changed(self, other: 'Assignment') -> bool:
        """
        Check if grade has changed compared to another assignment.

        Only compares semantically meaningful fields:
        - earned_points
        - max_points
        - exception
        - comment (if substantive)
        """
        if self.exception != other.exception:
            return True

        if self.earned_points != other.earned_points:
            return True

        if self.max_points != other.max_points:
            return True

        # Only consider comment changes if they're substantive (not "No comment")
        if self.comment != "No comment" or other.comment != "No comment":
            if self.comment != other.comment:
                return True

        return False


class Category(BaseModel):
    """
    Grading category with assignments.

    Attributes:
        category_id: Unique identifier from Schoology (0 for uncategorized)
        name: Category name
        weight: Category weight as percentage (None if not weighted)
        assignments: List of assignments in this category
    """
    category_id: int
    name: str
    weight: Optional[Decimal] = None
    assignments: list[Assignment] = Field(default_factory=list)

    @field_validator('weight', mode='before')
    @classmethod
    def parse_weight(cls, v):
        """Convert weight to Decimal"""
        if v is None or v == '':
            return None
        try:
            return Decimal(str(v))
        except:
            return None


class Period(BaseModel):
    """
    Grading period with categories.

    Attributes:
        period_id: Unique identifier (constructed from period title)
        name: Period name (e.g., "2025-2026 T1")
        categories: List of grading categories
    """
    period_id: str
    name: str
    categories: list[Category] = Field(default_factory=list)


class Section(BaseModel):
    """
    Course section with periods.

    Attributes:
        section_id: Unique identifier from Schoology API
        course_title: Course title
        section_title: Section title
        periods: List of grading periods
    """
    section_id: str
    course_title: str
    section_title: str
    periods: list[Period] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get full course name"""
        if self.section_title:
            return f"{self.course_title}: {self.section_title}"
        return self.course_title


class GradeData(BaseModel):
    """
    Complete grade data snapshot.

    Attributes:
        timestamp: When this snapshot was taken
        sections: List of all course sections
    """
    timestamp: datetime
    sections: list[Section] = Field(default_factory=list)

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Find assignment by ID across all sections/periods/categories"""
        for section in self.sections:
            for period in section.periods:
                for category in period.categories:
                    for assignment in category.assignments:
                        if assignment.assignment_id == assignment_id:
                            return assignment
        return None

    def get_all_assignments(self) -> list[tuple[Section, Period, Category, Assignment]]:
        """Get all assignments with their context (section, period, category)"""
        result = []
        for section in self.sections:
            for period in section.periods:
                for category in period.categories:
                    for assignment in category.assignments:
                        result.append((section, period, category, assignment))
        return result
