#!/usr/bin/env python3
"""
Schoology API Client for grade data retrieval
Uses OAuth 1.0a authentication
"""
import os
import logging
from typing import Dict, List, Any, Optional
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv


class SchoologyAPIClient:
    """Client for interacting with Schoology API"""

    BASE_URL = 'https://api.schoology.com/v1'

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize API client

        Args:
            api_key: Schoology API key (defaults to env var SCHOOLOGY_API_KEY)
            api_secret: Schoology API secret (defaults to env var SCHOOLOGY_API_SECRET)
        """
        load_dotenv()

        self.api_key = api_key or os.getenv('SCHOOLOGY_API_KEY')
        self.api_secret = api_secret or os.getenv('SCHOOLOGY_API_SECRET')

        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not provided. Set SCHOOLOGY_API_KEY and SCHOOLOGY_API_SECRET")

        self.session = OAuth1Session(
            client_key=self.api_key,
            client_secret=self.api_secret
        )

        self.logger = logging.getLogger(__name__)
        self._user_id: Optional[str] = None

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to API"""
        url = f'{self.BASE_URL}/{endpoint}'
        self.logger.debug(f"GET {url}")

        response = self.session.get(url)
        response.raise_for_status()

        return response.json()

    def get_user_id(self) -> str:
        """Get current user ID"""
        if not self._user_id:
            me = self._get('users/me')
            self._user_id = str(me['uid'])
            self.logger.info(f"Retrieved user ID: {self._user_id}")

        return self._user_id

    def get_sections(self) -> List[Dict[str, Any]]:
        """Get all sections/courses for current user"""
        user_id = self.get_user_id()
        data = self._get(f'users/{user_id}/sections')
        return data.get('section', [])

    def get_grades(self, section_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get grades for user

        Args:
            section_id: If provided, filter to specific section

        Returns:
            Grades data structure
        """
        user_id = self.get_user_id()

        if section_id:
            endpoint = f'users/{user_id}/grades?section_id={section_id}'
        else:
            endpoint = f'users/{user_id}/grades'

        return self._get(endpoint)

    def get_assignments(self, section_id: str) -> List[Dict[str, Any]]:
        """Get all assignments for a section"""
        data = self._get(f'sections/{section_id}/assignments')
        return data.get('assignment', [])

    def get_assignment_details(self, section_id: str, assignment_id: str) -> Dict[str, Any]:
        """Get detailed info for specific assignment"""
        return self._get(f'sections/{section_id}/assignments/{assignment_id}')

    def get_assignment_comments(self, section_id: str, assignment_id: str) -> List[Dict[str, Any]]:
        """Get comments/discussion for an assignment"""
        try:
            data = self._get(f'sections/{section_id}/assignments/{assignment_id}/comments')
            return data.get('comment', [])
        except Exception as e:
            self.logger.debug(f"Could not get comments for assignment {assignment_id}: {e}")
            return []

    def get_grading_categories(self, section_id: str) -> List[Dict[str, Any]]:
        """Get grading categories and weights for a section"""
        data = self._get(f'sections/{section_id}/grading_categories')
        return data.get('grading_category', [])

    def get_grading_scales(self, section_id: str) -> List[Dict[str, Any]]:
        """Get grading scale (letter grades) for a section"""
        data = self._get(f'sections/{section_id}/grading_scales')
        return data.get('grading_scale', [])
