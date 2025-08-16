"""
Shared grade data service interface for both scraper and dashboard components.
This abstracts the data access layer from the storage implementation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime


class GradeDataService(ABC):
    """Abstract interface for grade data operations."""
    
    @abstractmethod
    def save_snapshot(self, data: Dict) -> str:
        """Save a grade snapshot and return the timestamp."""
        pass
    
    @abstractmethod
    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent grade snapshot."""
        pass
    
    @abstractmethod
    def get_all_snapshots(self) -> List[Dict]:
        """Get all snapshots, sorted by date (newest first)."""
        pass
    
    @abstractmethod
    def get_snapshot_by_date(self, date: str) -> Optional[Dict]:
        """Get a specific snapshot by date."""
        pass


class DynamoDBGradeDataService(GradeDataService):
    """DynamoDB implementation of the grade data service."""
    
    def __init__(self):
        # Import here to avoid circular dependencies
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from dynamodb_manager import DynamoDBManager
        self.db = DynamoDBManager()
    
    def save_snapshot(self, data: Dict) -> str:
        """Save a grade snapshot and return the timestamp."""
        return self.db.add_entry(data)
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent grade snapshot."""
        snapshots = self.get_all_snapshots()
        return snapshots[0]['Data'] if snapshots else None
    
    def get_all_snapshots(self) -> List[Dict]:
        """Get all snapshots, sorted by date (newest first)."""
        response = self.db.table.scan(
            ProjectionExpression='#date, #data',
            ExpressionAttributeNames={
                '#date': 'Date',
                '#data': 'Data'
            }
        )
        items = response.get('Items', [])
        if not items:
            return []
        
        # Sort items by date, newest first
        return sorted(items, key=lambda x: x['Date'], reverse=True)
    
    def get_snapshot_by_date(self, date: str) -> Optional[Dict]:
        """Get a specific snapshot by date."""
        return self.db.read_entry(date)


# Factory function to create the appropriate service
def create_grade_data_service() -> GradeDataService:
    """Create and return a grade data service instance."""
    return DynamoDBGradeDataService()