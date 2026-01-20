"""
Tests for API grade fetcher with mocked API client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from api.fetch_grades_v2 import APIGradeFetcherV2
from shared.models import GradeData


@pytest.fixture
def mock_api_client():
    """Create mocked SchoologyAPIClient"""
    with patch('api.fetch_grades_v2.SchoologyAPIClient') as MockClient:
        client = MockClient.return_value
        yield client


@pytest.fixture
def sample_sections():
    """Sample sections data from API"""
    return [
        {
            'id': '12345',
            'course_title': 'Math 7',
            'section_title': 'Period 1'
        },
        {
            'id': '12346',
            'course_title': 'English 7',
            'section_title': 'Period 2'
        }
    ]


@pytest.fixture
def sample_grades():
    """Sample grades data from API"""
    return {
        'section': [
            {
                'section_id': '12345',
                'period': [
                    {
                        'period_title': '2024-2025 T1',
                        'assignment': [
                            {
                                'assignment_id': 100,
                                'category_id': 1,
                                'grade': '85',
                                'max_points': '100',
                                'exception': 0,
                                'comment': ''
                            },
                            {
                                'assignment_id': 101,
                                'category_id': 1,
                                'grade': '',
                                'max_points': '10',
                                'exception': 3,  # Missing
                                'comment': ''
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_categories():
    """Sample grading categories from API"""
    return [
        {'id': 1, 'title': 'Homework', 'weight': '30'},
        {'id': 2, 'title': 'Tests', 'weight': '70'}
    ]


class TestAPIGradeFetcher:
    """Tests for APIGradeFetcherV2"""

    def test_fetch_all_grades_returns_grade_data(self, mock_api_client, sample_sections, sample_grades, sample_categories):
        """Test that fetch returns properly structured GradeData"""
        mock_api_client.get_sections.return_value = sample_sections
        mock_api_client.get_grades.return_value = sample_grades
        mock_api_client.get_grading_categories.return_value = sample_categories
        mock_api_client.get_assignment_details.return_value = {'title': 'Test Assignment'}
        mock_api_client.get_assignment_comments.return_value = []

        fetcher = APIGradeFetcherV2()
        result = fetcher.fetch_all_grades()

        assert isinstance(result, GradeData)
        assert result.timestamp is not None

    def test_fetch_creates_sections(self, mock_api_client, sample_sections, sample_grades, sample_categories):
        """Test that sections are created from API data"""
        mock_api_client.get_sections.return_value = sample_sections
        mock_api_client.get_grades.return_value = sample_grades
        mock_api_client.get_grading_categories.return_value = sample_categories
        mock_api_client.get_assignment_details.return_value = {'title': 'Test'}
        mock_api_client.get_assignment_comments.return_value = []

        fetcher = APIGradeFetcherV2()
        result = fetcher.fetch_all_grades()

        assert len(result.sections) == 1
        assert result.sections[0].section_id == '12345'
        assert result.sections[0].course_title == 'Math 7'

    def test_fetch_creates_assignments(self, mock_api_client, sample_sections, sample_grades, sample_categories):
        """Test that assignments are created from API data"""
        mock_api_client.get_sections.return_value = sample_sections
        mock_api_client.get_grades.return_value = sample_grades
        mock_api_client.get_grading_categories.return_value = sample_categories
        mock_api_client.get_assignment_details.return_value = {'title': 'Test Assignment'}
        mock_api_client.get_assignment_comments.return_value = []

        fetcher = APIGradeFetcherV2()
        result = fetcher.fetch_all_grades()

        assignments = result.get_all_assignments()
        assert len(assignments) == 2


class TestGradeParsing:
    """Tests for grade value parsing"""

    def test_parse_numeric_grade(self, mock_api_client):
        """Test parsing numeric grade values"""
        fetcher = APIGradeFetcherV2()

        grade_obj = {'grade': '85', 'max_points': '100', 'exception': 0}
        earned, max_pts, exception = fetcher._parse_grade(grade_obj)

        assert earned == Decimal('85')
        assert max_pts == Decimal('100')
        assert exception is None

    def test_parse_missing_exception(self, mock_api_client):
        """Test parsing Missing exception status"""
        fetcher = APIGradeFetcherV2()

        grade_obj = {'grade': '', 'max_points': '10', 'exception': 3}
        earned, max_pts, exception = fetcher._parse_grade(grade_obj)

        assert exception == 'Missing'
        assert earned is None

    def test_parse_excused_exception(self, mock_api_client):
        """Test parsing Excused exception status"""
        fetcher = APIGradeFetcherV2()

        grade_obj = {'grade': '', 'max_points': '10', 'exception': 1}
        earned, max_pts, exception = fetcher._parse_grade(grade_obj)

        assert exception == 'Excused'

    def test_parse_incomplete_exception(self, mock_api_client):
        """Test parsing Incomplete exception status"""
        fetcher = APIGradeFetcherV2()

        grade_obj = {'grade': '', 'max_points': '10', 'exception': 2}
        earned, max_pts, exception = fetcher._parse_grade(grade_obj)

        assert exception == 'Incomplete'

    def test_parse_decimal_grade(self, mock_api_client):
        """Test parsing decimal grade values"""
        fetcher = APIGradeFetcherV2()

        grade_obj = {'grade': '8.5', 'max_points': '10', 'exception': 0}
        earned, max_pts, exception = fetcher._parse_grade(grade_obj)

        assert earned == Decimal('8.5')
        assert max_pts == Decimal('10')

    def test_parse_empty_grade(self, mock_api_client):
        """Test parsing empty grade (not graded)"""
        fetcher = APIGradeFetcherV2()

        grade_obj = {'grade': '', 'max_points': '10', 'exception': 0}
        earned, max_pts, exception = fetcher._parse_grade(grade_obj)

        assert earned is None
        assert max_pts == Decimal('10')


class TestDueDateParsing:
    """Tests for due date parsing"""

    def test_parse_valid_due_date(self, mock_api_client):
        """Test parsing valid due date string"""
        fetcher = APIGradeFetcherV2()

        result = fetcher._parse_due_date('2025-01-15 23:59:00')

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_empty_due_date(self, mock_api_client):
        """Test parsing empty due date returns None"""
        fetcher = APIGradeFetcherV2()

        result = fetcher._parse_due_date('')

        assert result is None

    def test_parse_none_due_date(self, mock_api_client):
        """Test parsing None due date returns None"""
        fetcher = APIGradeFetcherV2()

        result = fetcher._parse_due_date(None)

        assert result is None


class TestSectionMatching:
    """Tests for section ID matching logic"""

    def test_direct_section_match(self, mock_api_client):
        """Test direct section ID matching"""
        sections = [{'id': '12345', 'course_title': 'Math', 'section_title': 'P1'}]
        grades = {
            'section': [
                {'section_id': '12345', 'period': []}
            ]
        }

        mock_api_client.get_sections.return_value = sections
        mock_api_client.get_grades.return_value = grades
        mock_api_client.get_grading_categories.return_value = []

        fetcher = APIGradeFetcherV2()
        result = fetcher.fetch_all_grades()

        assert len(result.sections) == 1
        assert result.sections[0].course_title == 'Math'

    def test_offset_section_matching(self, mock_api_client):
        """Test section ID matching with offset (Schoology quirk)"""
        # Enrollment ID differs from grade section ID by offset
        sections = [{'id': '12346', 'course_title': 'Math', 'section_title': 'P1'}]
        grades = {
            'section': [
                {'section_id': '12345', 'period': []}  # Off by 1
            ]
        }

        mock_api_client.get_sections.return_value = sections
        mock_api_client.get_grades.return_value = grades
        mock_api_client.get_grading_categories.return_value = []

        fetcher = APIGradeFetcherV2()
        result = fetcher.fetch_all_grades()

        # Should match via offset
        assert len(result.sections) == 1
        assert result.sections[0].course_title == 'Math'


class TestCommentRetrieval:
    """Tests for assignment comment retrieval"""

    def test_comment_from_grade_object(self, mock_api_client):
        """Test comment retrieval from grade data"""
        mock_api_client.get_assignment_comments.return_value = []

        fetcher = APIGradeFetcherV2()
        grade_obj = {'comment': 'Great work!'}

        result = fetcher._get_assignment_comment('12345', '100', grade_obj)

        assert result == 'Great work!'

    def test_comment_from_api_endpoint(self, mock_api_client):
        """Test comment retrieval from comments API"""
        mock_api_client.get_assignment_comments.return_value = [
            {'comment': 'From API', 'created': 1000}
        ]

        fetcher = APIGradeFetcherV2()
        grade_obj = {'comment': ''}

        result = fetcher._get_assignment_comment('12345', '100', grade_obj)

        assert result == 'From API'

    def test_no_comment_returns_default(self, mock_api_client):
        """Test that missing comment returns default"""
        mock_api_client.get_assignment_comments.return_value = []

        fetcher = APIGradeFetcherV2()
        grade_obj = {}

        result = fetcher._get_assignment_comment('12345', '100', grade_obj)

        assert result == 'No comment'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
