#!/usr/bin/env python3
"""
Compare data from API vs Scraper to identify deltas
Focus on: grades, assignments, and especially comments
"""
import json
import sys
from typing import Dict, Any, List, Tuple
from collections import defaultdict


class DataComparator:
    """Compare scraper data vs API data"""

    def __init__(self, scraper_file: str, api_file: str):
        with open(scraper_file, 'r') as f:
            self.scraper_data = json.load(f)

        with open(api_file, 'r') as f:
            self.api_data = json.load(f)

        self.deltas = {
            'missing_in_api': [],
            'missing_in_scraper': [],
            'grade_mismatches': [],
            'comment_differences': [],
            'due_date_differences': [],
            'extra_data_in_scraper': [],
            'extra_data_in_api': []
        }

    def _normalize_grade(self, grade_str: str) -> str:
        """Normalize grade string for comparison"""
        if not grade_str:
            return ''

        grade_str = grade_str.strip().lower()

        # Normalize common variations
        if grade_str in ['not graded', 'not_graded', 'none', '']:
            return 'not_graded'

        if grade_str in ['missing', 'incomplete']:
            return 'missing'

        return grade_str

    def _find_assignment_in_data(self, title: str, data: Dict[str, Any]) -> List[Tuple[str, str, Dict]]:
        """Find assignment by title across all courses/periods/categories"""
        results = []

        for course_name, course in data.items():
            for period_name, period in course.get('periods', {}).items():
                for category_name, category in period.get('categories', {}).items():
                    for assignment in category.get('assignments', []):
                        if assignment.get('title') == title:
                            results.append((course_name, period_name, category_name, assignment))

        return results

    def compare_assignments(self):
        """Compare all assignments between datasets"""
        print("\n" + "=" * 80)
        print("ASSIGNMENT COMPARISON")
        print("=" * 80)

        # Build sets of assignment titles
        scraper_assignments = set()
        api_assignments = set()

        # Collect from scraper
        for course in self.scraper_data.values():
            for period in course.get('periods', {}).values():
                for category in period.get('categories', {}).values():
                    for assignment in category.get('assignments', []):
                        scraper_assignments.add(assignment['title'])

        # Collect from API
        for course in self.api_data.values():
            for period in course.get('periods', {}).values():
                for category in period.get('categories', {}).values():
                    for assignment in category.get('assignments', []):
                        api_assignments.add(assignment['title'])

        # Find missing assignments
        missing_in_api = scraper_assignments - api_assignments
        missing_in_scraper = api_assignments - scraper_assignments

        if missing_in_api:
            print(f"\n⚠️  {len(missing_in_api)} assignments in SCRAPER but NOT in API:")
            for title in sorted(missing_in_api)[:10]:  # Show first 10
                print(f"  - {title}")
            if len(missing_in_api) > 10:
                print(f"  ... and {len(missing_in_api) - 10} more")

            self.deltas['missing_in_api'] = list(missing_in_api)

        if missing_in_scraper:
            print(f"\n⚠️  {len(missing_in_scraper)} assignments in API but NOT in SCRAPER:")
            for title in sorted(missing_in_scraper)[:10]:
                print(f"  - {title}")
            if len(missing_in_scraper) > 10:
                print(f"  ... and {len(missing_in_scraper) - 10} more")

            self.deltas['missing_in_scraper'] = list(missing_in_scraper)

        # Compare matching assignments
        matching_assignments = scraper_assignments & api_assignments
        print(f"\n✅ {len(matching_assignments)} assignments found in BOTH datasets")

        return matching_assignments

    def compare_grades(self, matching_assignments: set):
        """Compare grades for matching assignments"""
        print("\n" + "=" * 80)
        print("GRADE COMPARISON")
        print("=" * 80)

        grade_mismatches = []

        for title in matching_assignments:
            scraper_matches = self._find_assignment_in_data(title, self.scraper_data)
            api_matches = self._find_assignment_in_data(title, self.api_data)

            if scraper_matches and api_matches:
                # Compare first match (should usually only be one)
                scraper_assignment = scraper_matches[0][3]
                api_assignment = api_matches[0][3]

                scraper_grade = self._normalize_grade(scraper_assignment.get('grade', ''))
                api_grade = self._normalize_grade(api_assignment.get('grade', ''))

                if scraper_grade != api_grade:
                    grade_mismatches.append({
                        'title': title,
                        'scraper_grade': scraper_assignment.get('grade'),
                        'api_grade': api_assignment.get('grade')
                    })

        if grade_mismatches:
            print(f"\n⚠️  {len(grade_mismatches)} GRADE MISMATCHES:")
            for mismatch in grade_mismatches[:10]:
                print(f"  Assignment: {mismatch['title']}")
                print(f"    Scraper: {mismatch['scraper_grade']}")
                print(f"    API:     {mismatch['api_grade']}")
                print()

            self.deltas['grade_mismatches'] = grade_mismatches
        else:
            print("\n✅ All grades MATCH between scraper and API")

    def compare_comments(self, matching_assignments: set):
        """Compare comments - THIS IS CRITICAL"""
        print("\n" + "=" * 80)
        print("COMMENT COMPARISON (CRITICAL)")
        print("=" * 80)

        comment_differences = []
        scraper_has_comments = 0
        api_has_comments = 0

        for title in matching_assignments:
            scraper_matches = self._find_assignment_in_data(title, self.scraper_data)
            api_matches = self._find_assignment_in_data(title, self.api_data)

            if scraper_matches and api_matches:
                scraper_assignment = scraper_matches[0][3]
                api_assignment = api_matches[0][3]

                scraper_comment = scraper_assignment.get('comment', 'No comment')
                api_comment = api_assignment.get('comment', 'No comment')

                # Count non-default comments
                if scraper_comment and scraper_comment != 'No comment':
                    scraper_has_comments += 1

                if api_comment and api_comment != 'No comment':
                    api_has_comments += 1

                # Compare
                if scraper_comment != api_comment:
                    comment_differences.append({
                        'title': title,
                        'scraper_comment': scraper_comment,
                        'api_comment': api_comment
                    })

        print(f"\nComment Statistics:")
        print(f"  Scraper has {scraper_has_comments} assignments with actual comments")
        print(f"  API has {api_has_comments} assignments with actual comments")

        if comment_differences:
            print(f"\n⚠️  {len(comment_differences)} COMMENT DIFFERENCES:")
            for diff in comment_differences[:10]:
                print(f"  Assignment: {diff['title']}")
                print(f"    Scraper: {diff['scraper_comment']}")
                print(f"    API:     {diff['api_comment']}")
                print()

            if len(comment_differences) > 10:
                print(f"  ... and {len(comment_differences) - 10} more differences")

            self.deltas['comment_differences'] = comment_differences
        else:
            print("\n✅ All comments MATCH")

    def compare_due_dates(self, matching_assignments: set):
        """Compare due dates"""
        print("\n" + "=" * 80)
        print("DUE DATE COMPARISON")
        print("=" * 80)

        due_date_diffs = []
        scraper_with_dates = 0
        api_with_dates = 0

        for title in matching_assignments:
            scraper_matches = self._find_assignment_in_data(title, self.scraper_data)
            api_matches = self._find_assignment_in_data(title, self.api_data)

            if scraper_matches and api_matches:
                scraper_assignment = scraper_matches[0][3]
                api_assignment = api_matches[0][3]

                scraper_due = scraper_assignment.get('due_date')
                api_due = api_assignment.get('due_date')

                if scraper_due:
                    scraper_with_dates += 1
                if api_due:
                    api_with_dates += 1

                if scraper_due != api_due:
                    due_date_diffs.append({
                        'title': title,
                        'scraper_due': scraper_due,
                        'api_due': api_due
                    })

        print(f"\nDue Date Statistics:")
        print(f"  Scraper: {scraper_with_dates} assignments with due dates")
        print(f"  API:     {api_with_dates} assignments with due dates")

        if due_date_diffs:
            print(f"\n⚠️  {len(due_date_diffs)} DUE DATE DIFFERENCES:")
            for diff in due_date_diffs[:5]:
                print(f"  Assignment: {diff['title']}")
                print(f"    Scraper: {diff['scraper_due']}")
                print(f"    API:     {diff['api_due']}")
                print()

            self.deltas['due_date_differences'] = due_date_diffs

    def generate_summary(self):
        """Generate comprehensive summary"""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        # Count totals
        scraper_total = sum(
            len(cat['assignments'])
            for course in self.scraper_data.values()
            for period in course.get('periods', {}).values()
            for cat in period.get('categories', {}).values()
        )

        api_total = sum(
            len(cat['assignments'])
            for course in self.api_data.values()
            for period in course.get('periods', {}).values()
            for cat in period.get('categories', {}).values()
        )

        print(f"\nDataset Sizes:")
        print(f"  Scraper: {len(self.scraper_data)} courses, {scraper_total} total assignments")
        print(f"  API:     {len(self.api_data)} courses, {api_total} total assignments")

        print(f"\nDelta Summary:")
        print(f"  Missing in API:        {len(self.deltas['missing_in_api'])} assignments")
        print(f"  Missing in Scraper:    {len(self.deltas['missing_in_scraper'])} assignments")
        print(f"  Grade Mismatches:      {len(self.deltas['grade_mismatches'])} assignments")
        print(f"  Comment Differences:   {len(self.deltas['comment_differences'])} assignments")
        print(f"  Due Date Differences:  {len(self.deltas['due_date_differences'])} assignments")

        # Critical findings
        print("\n" + "=" * 80)
        print("CRITICAL FINDINGS")
        print("=" * 80)

        critical_issues = []

        if len(self.deltas['missing_in_api']) > 0:
            critical_issues.append(f"❌ API is missing {len(self.deltas['missing_in_api'])} assignments that scraper found")

        if len(self.deltas['grade_mismatches']) > 0:
            critical_issues.append(f"⚠️  {len(self.deltas['grade_mismatches'])} grade mismatches between API and scraper")

        if len(self.deltas['comment_differences']) > 0:
            critical_issues.append(f"⚠️  {len(self.deltas['comment_differences'])} comment differences")

        if critical_issues:
            for issue in critical_issues:
                print(f"  {issue}")
        else:
            print("  ✅ No critical issues - API data matches scraper data")

        # Save detailed delta report
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(script_dir), 'data')
        report_file = os.path.join(data_dir, 'api_scraper_comparison.json')

        with open(report_file, 'w') as f:
            json.dump(self.deltas, f, indent=2)

        print(f"\n📄 Detailed delta report saved to: {report_file}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_data.py <scraper_json_file> <api_json_file>")
        sys.exit(1)

    scraper_file = sys.argv[1]
    api_file = sys.argv[2]

    print(f"Comparing:")
    print(f"  Scraper: {scraper_file}")
    print(f"  API:     {api_file}")

    comparator = DataComparator(scraper_file, api_file)

    # Run comparisons
    matching = comparator.compare_assignments()
    comparator.compare_grades(matching)
    comparator.compare_comments(matching)
    comparator.compare_due_dates(matching)
    comparator.generate_summary()


if __name__ == '__main__':
    main()
