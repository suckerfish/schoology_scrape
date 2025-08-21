import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from deepdiff import DeepDiff
from dynamodb_manager import DynamoDBManager

class GradeComparator:
    """Handles change detection logic using DeepDiff"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_service = DynamoDBManager()
    
    def detect_changes(self, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Compare new data with the latest snapshot to detect changes
        
        Args:
            new_data: New grade data to compare
            
        Returns:
            Dict containing change information, or None if no changes
        """
        try:
            # Get the latest snapshot from the data service
            # For now, just return None since the DynamoDBManager doesn't have this method
            # This will treat all comparisons as "initial" data
            latest_snapshot = None
            
            if not latest_snapshot:
                self.logger.info("No previous snapshot found - treating as initial data")
                return {
                    'type': 'initial',
                    'message': 'Initial grade data captured',
                    'data': new_data
                }
            
            # Extract the actual data from the snapshot
            latest_data = latest_snapshot.get('data', {})
            
            # Perform deep comparison
            diff = DeepDiff(latest_data, new_data, ignore_order=True)
            
            if diff:
                self.logger.info("Changes detected in grade data")
                changes = self._process_changes(diff, latest_data, new_data)
                return changes
            else:
                self.logger.info("No changes detected in grade data")
                return None
                
        except Exception as e:
            self.logger.error(f"Error detecting changes: {e}")
            return None
    
    def detect_changes_from_file(self, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Compare new data with the latest local file to detect changes
        
        Args:
            new_data: New grade data to compare
            
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
                changes = self._process_changes(diff, latest_data, new_data)
                return changes
            else:
                self.logger.info("No changes detected compared to latest file")
                return None
                
        except Exception as e:
            self.logger.error(f"Error detecting changes from file: {e}")
            return None
    
    def _process_changes(self, diff: DeepDiff, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process DeepDiff output into a structured change report
        
        Args:
            diff: DeepDiff result
            old_data: Previous data
            new_data: New data
            
        Returns:
            Dict containing processed change information
        """
        changes = {
            'type': 'update',
            'summary': self._generate_change_summary(diff),
            'detailed_changes': self._extract_detailed_changes(diff),
            'diff_raw': diff,
            'old_data': old_data,
            'new_data': new_data
        }
        
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
    
    def _extract_detailed_changes(self, diff: DeepDiff) -> List[Dict[str, Any]]:
        """Extract detailed change information for notifications"""
        detailed_changes = []
        
        # Process value changes
        if 'values_changed' in diff:
            for path, change in diff['values_changed'].items():
                detailed_changes.append({
                    'type': 'value_changed',
                    'path': path,
                    'old_value': change['old_value'],
                    'new_value': change['new_value']
                })
        
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
        
        message = f"Grade changes detected: {changes['summary']}\n\n"
        
        # Add detailed changes
        detailed_changes = changes.get('detailed_changes', [])
        if detailed_changes:
            message += "Detailed changes:\n"
            for change in detailed_changes[:10]:  # Limit to first 10 changes
                if change['type'] == 'value_changed':
                    message += f"• {change['path']}: {change['old_value']} → {change['new_value']}\n"
                elif change['type'] == 'item_added':
                    message += f"• Added: {change['path']} = {change['value']}\n"
                elif change['type'] == 'item_removed':
                    message += f"• Removed: {change['path']} = {change['value']}\n"
            
            if len(detailed_changes) > 10:
                message += f"• ... and {len(detailed_changes) - 10} more changes\n"
        
        return message