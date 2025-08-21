#!/usr/bin/env python3
"""
Test the new Gemini 2.5 Flash model and prompt with actual grade change data
"""

import json
import os
from pathlib import Path
from notifications.gemini_provider import GeminiProvider
from notifications.base import NotificationMessage
from pipeline.comparator import GradeComparator
from shared.config import get_config

def test_new_gemini_prompt():
    """Test the new Gemini prompt with real grade change data"""
    print("🧪 Testing new Gemini 2.5 Flash model and prompt...")
    
    # Load configuration
    try:
        config = get_config()
        print(f"✅ Configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return
    
    # Initialize Gemini provider
    gemini_config = {
        'enabled': True,
        'api_key': config.notifications.gemini_api_key
    }
    
    if not gemini_config['api_key']:
        print("❌ No Gemini API key found in configuration")
        return
    
    try:
        gemini_provider = GeminiProvider(gemini_config)
        print(f"✅ Gemini provider initialized")
        print(f"🤖 Model: gemini-2.5-flash")
    except Exception as e:
        print(f"❌ Failed to initialize Gemini provider: {e}")
        return
    
    # Use mock change data for testing
    try:
        print("📂 Using mock change data for testing...")
        changes = {
                'type': 'update',
                'summary': '5 value(s) changed, 3 item(s) added',
                'detailed_changes': [
                    {
                        'type': 'item_added',
                        'path': "root['Art: Section 33']['periods']['2025-2026']['categories']['Artwork Analysis Notebook (20%)']",
                        'value': 'New category added'
                    },
                    {
                        'type': 'item_added', 
                        'path': "root['Accelerated Math 7B/8: Section 28']['periods']['2025-2026']['categories']['cw/hw (20%)']['assignments'][1]",
                        'value': 'New assignment added'
                    },
                    {
                        'type': 'value_changed',
                        'path': "root['Art: Section 33']['periods']['2025-2026']['categories']['Projects and Performance Tasks (50%)']['assignments'][2]['grade']",
                        'old_value': 'Not graded',
                        'new_value': 'A-'
                    },
                    {
                        'type': 'value_changed',
                        'path': "root['Art: Section 33']['periods']['2025-2026']['categories']['Projects and Performance Tasks (50%)']['assignments'][0]['comment']",
                        'old_value': 'No comment',
                        'new_value': 'Great work on color theory!'
                    }
                ]
            }
        
        # Create a comparator just for the formatting function
        comparator = GradeComparator()
        
        if not changes:
            print("❌ No changes detected or comparison failed")
            return
        
        # Format the changes for notification
        formatted_message = comparator.format_changes_for_notification(changes)
        print(f"📝 Formatted message:\n{formatted_message}")
        
        # Create notification message
        message = NotificationMessage(
            title="Schoology Grade Changes Detected",
            content=formatted_message,
            priority="normal",
            metadata={
                'grade_changes': changes,
                'timestamp': changes.get('timestamp'),
                'change_type': changes.get('type', 'unknown')
            }
        )
        
        print(f"\n🚀 Sending to Gemini for analysis...")
        
        # Test the Gemini provider
        success = gemini_provider.send(message)
        
        if success:
            print(f"✅ Gemini analysis completed successfully!")
            
            # Extract and display the AI analysis
            ai_analysis = message.metadata.get('ai_analysis', 'No analysis generated')
            print(f"\n🤖 AI Analysis Output:")
            print("=" * 50)
            print(ai_analysis)
            print("=" * 50)
            
            # Validate the output format
            print(f"\n📊 Validation:")
            
            # Check if it follows the new prompt guidelines
            analysis_lower = ai_analysis.lower()
            
            # Good indicators (what we want)
            good_indicators = [
                'new assignment' in analysis_lower,
                'added' in analysis_lower,
                'grade change' in analysis_lower,
                '→' in ai_analysis or '->' in ai_analysis  # Grade change indicators
            ]
            
            # Bad indicators (what we don't want)
            bad_indicators = [
                'recommend' in analysis_lower,
                'suggestion' in analysis_lower,
                'should' in analysis_lower,
                'pattern' in analysis_lower,
                'concern' in analysis_lower,
                'insight' in analysis_lower
            ]
            
            good_count = sum(good_indicators)
            bad_count = sum(bad_indicators)
            
            print(f"✅ Good indicators found: {good_count}/4")
            print(f"❌ Bad indicators found: {bad_count}/6")
            
            if good_count >= 2 and bad_count == 0:
                print(f"🎉 VALIDATION PASSED: Output follows new prompt guidelines!")
            elif bad_count == 0:
                print(f"⚠️  PARTIAL PASS: No unwanted content, but could be more specific")
            else:
                print(f"❌ VALIDATION FAILED: Contains unwanted recommendations/analysis")
                
        else:
            print(f"❌ Gemini analysis failed")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_gemini_prompt()