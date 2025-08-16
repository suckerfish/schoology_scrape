"""
Enhanced grade data service with caching, error handling, and validation.
This builds upon the basic service interface with production-ready features.
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps
import json


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration."""
    data: Any
    created_at: datetime
    ttl_seconds: int
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)


class ServiceCache:
    """Simple in-memory cache for service operations."""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            logger.debug(f"Cache hit for key: {key}")
            return entry.data
        elif entry:
            # Remove expired entry
            del self._cache[key]
            logger.debug(f"Cache miss (expired) for key: {key}")
        else:
            logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set cached value with TTL."""
        self._cache[key] = CacheEntry(
            data=value,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds
        )
        logger.debug(f"Cache set for key: {key}, TTL: {ttl_seconds}s")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("Cache cleared")


def retry_on_failure(max_retries: int = 3, delay_seconds: int = 2):
    """Decorator to retry failed operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay_seconds}s...")
                        time.sleep(delay_seconds)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


class GradeDataValidationError(Exception):
    """Raised when grade data validation fails."""
    pass


class GradeDataServiceError(Exception):
    """Base exception for grade data service operations."""
    pass


class EnhancedGradeDataService(ABC):
    """Enhanced abstract interface for grade data operations."""
    
    @abstractmethod
    def save_snapshot(self, data: Dict, validate: bool = True) -> str:
        """Save a grade snapshot with optional validation."""
        pass
    
    @abstractmethod
    def get_latest_snapshot(self, use_cache: bool = True) -> Optional[Dict]:
        """Get the most recent grade snapshot with caching support."""
        pass
    
    @abstractmethod
    def get_all_snapshots(self, use_cache: bool = True, limit: Optional[int] = None) -> List[Dict]:
        """Get all snapshots with caching and optional limit."""
        pass
    
    @abstractmethod
    def get_snapshot_by_date(self, date: str, use_cache: bool = True) -> Optional[Dict]:
        """Get a specific snapshot by date with caching."""
        pass
    
    @abstractmethod
    def get_snapshots_in_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get snapshots within a date range."""
        pass
    
    @abstractmethod
    def delete_snapshot(self, date: str) -> bool:
        """Delete a specific snapshot."""
        pass
    
    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about stored snapshots."""
        pass


class EnhancedDynamoDBGradeDataService(EnhancedGradeDataService):
    """Enhanced DynamoDB implementation with caching and error handling."""
    
    def __init__(self, config=None):
        # Import here to avoid circular dependencies
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from dynamodb_manager import DynamoDBManager
        
        # Initialize cache and config
        self.cache = ServiceCache()
        self.config = config
        
        # Get cache TTL from config or use default
        self.cache_ttl = getattr(config.app, 'cache_ttl_seconds', 300) if config else 300
        self.max_retries = getattr(config.app, 'max_retries', 3) if config else 3
        self.retry_delay = getattr(config.app, 'retry_delay_seconds', 2) if config else 2
        
        try:
            self.db = DynamoDBManager()
            logger.info("DynamoDB connection established")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB connection: {e}")
            raise GradeDataServiceError(f"Database initialization failed: {e}")
    
    def validate_grade_data(self, data: Dict) -> None:
        """Validate grade data structure."""
        if not isinstance(data, dict):
            raise GradeDataValidationError("Grade data must be a dictionary")
        
        if not data:
            raise GradeDataValidationError("Grade data cannot be empty")
        
        # Validate basic structure - each course should have periods
        for course_name, course_data in data.items():
            if not isinstance(course_data, dict):
                raise GradeDataValidationError(f"Course '{course_name}' data must be a dictionary")
            
            if 'periods' not in course_data:
                raise GradeDataValidationError(f"Course '{course_name}' missing 'periods' key")
            
            # Validate periods structure
            for period_name, period_data in course_data['periods'].items():
                if 'categories' not in period_data:
                    raise GradeDataValidationError(f"Period '{period_name}' in course '{course_name}' missing 'categories' key")
        
        logger.debug("Grade data validation passed")
    
    @retry_on_failure(max_retries=3, delay_seconds=2)
    def save_snapshot(self, data: Dict, validate: bool = True) -> str:
        """Save a grade snapshot with validation and retry logic."""
        try:
            if validate:
                self.validate_grade_data(data)
            
            timestamp = self.db.add_entry(data)
            
            # Clear relevant caches
            self.cache.clear()
            
            logger.info(f"Snapshot saved successfully: {timestamp}")
            return timestamp
            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            raise GradeDataServiceError(f"Save operation failed: {e}")
    
    def get_latest_snapshot(self, use_cache: bool = True) -> Optional[Dict]:
        """Get the most recent grade snapshot with caching."""
        cache_key = "latest_snapshot"
        
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        try:
            snapshots = self.get_all_snapshots(use_cache=False, limit=1)
            result = snapshots[0]['Data'] if snapshots else None
            
            if use_cache and result:
                self.cache.set(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get latest snapshot: {e}")
            raise GradeDataServiceError(f"Get latest snapshot failed: {e}")
    
    @retry_on_failure(max_retries=3, delay_seconds=2)
    def get_all_snapshots(self, use_cache: bool = True, limit: Optional[int] = None) -> List[Dict]:
        """Get all snapshots with caching and optional limit."""
        cache_key = f"all_snapshots_limit_{limit}"
        
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        try:
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
            sorted_items = sorted(items, key=lambda x: x['Date'], reverse=True)
            
            # Apply limit if specified
            if limit:
                sorted_items = sorted_items[:limit]
            
            if use_cache:
                self.cache.set(cache_key, sorted_items, self.cache_ttl)
            
            logger.debug(f"Retrieved {len(sorted_items)} snapshots")
            return sorted_items
            
        except Exception as e:
            logger.error(f"Failed to get all snapshots: {e}")
            raise GradeDataServiceError(f"Get all snapshots failed: {e}")
    
    @retry_on_failure(max_retries=3, delay_seconds=2)
    def get_snapshot_by_date(self, date: str, use_cache: bool = True) -> Optional[Dict]:
        """Get a specific snapshot by date with caching."""
        cache_key = f"snapshot_{date}"
        
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        try:
            result = self.db.read_entry(date)
            
            if use_cache and result:
                self.cache.set(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get snapshot by date {date}: {e}")
            raise GradeDataServiceError(f"Get snapshot by date failed: {e}")
    
    def get_snapshots_in_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get snapshots within a date range."""
        try:
            all_snapshots = self.get_all_snapshots(use_cache=True)
            
            # Filter by date range
            filtered_snapshots = [
                snapshot for snapshot in all_snapshots
                if start_date <= snapshot['Date'] <= end_date
            ]
            
            logger.debug(f"Retrieved {len(filtered_snapshots)} snapshots in range {start_date} to {end_date}")
            return filtered_snapshots
            
        except Exception as e:
            logger.error(f"Failed to get snapshots in range: {e}")
            raise GradeDataServiceError(f"Get snapshots in range failed: {e}")
    
    @retry_on_failure(max_retries=3, delay_seconds=2)
    def delete_snapshot(self, date: str) -> bool:
        """Delete a specific snapshot."""
        try:
            response = self.db.table.delete_item(
                Key={'Date': date},
                ReturnValues='ALL_OLD'
            )
            
            success = 'Attributes' in response
            if success:
                # Clear caches since data changed
                self.cache.clear()
                logger.info(f"Snapshot deleted: {date}")
            else:
                logger.warning(f"Snapshot not found for deletion: {date}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete snapshot {date}: {e}")
            raise GradeDataServiceError(f"Delete snapshot failed: {e}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about stored snapshots."""
        cache_key = "summary_stats"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            snapshots = self.get_all_snapshots(use_cache=True)
            
            if not snapshots:
                return {
                    "total_snapshots": 0,
                    "date_range": None,
                    "latest_snapshot_date": None,
                    "oldest_snapshot_date": None
                }
            
            dates = [snapshot['Date'] for snapshot in snapshots]
            latest_date = max(dates)
            oldest_date = min(dates)
            
            stats = {
                "total_snapshots": len(snapshots),
                "latest_snapshot_date": latest_date,
                "oldest_snapshot_date": oldest_date,
                "date_range": f"{oldest_date} to {latest_date}",
                "cache_stats": {
                    "cache_entries": len(self.cache._cache),
                    "cache_ttl_seconds": self.cache_ttl
                }
            }
            
            # Cache stats for 1 minute
            self.cache.set(cache_key, stats, 60)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            raise GradeDataServiceError(f"Get summary stats failed: {e}")


def create_enhanced_grade_data_service(config=None) -> EnhancedGradeDataService:
    """Create and return an enhanced grade data service instance."""
    return EnhancedDynamoDBGradeDataService(config=config)


if __name__ == "__main__":
    # Test the enhanced service
    try:
        service = create_enhanced_grade_data_service()
        print("✅ Enhanced service created successfully")
        
        # Test summary stats
        stats = service.get_summary_stats()
        print(f"📊 Summary stats: {stats}")
        
        # Test latest snapshot
        latest = service.get_latest_snapshot()
        print(f"📈 Latest snapshot available: {latest is not None}")
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")