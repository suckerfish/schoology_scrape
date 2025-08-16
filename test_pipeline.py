#!/usr/bin/env python3
"""
Test script for the refactored Phase 3 pipeline
"""
import logging
import sys
from pathlib import Path
from pipeline.orchestrator import GradePipeline
from pipeline.scraper import GradeScraper
from pipeline.comparator import GradeComparator
from pipeline.notifier import GradeNotifier
from pipeline.error_handling import error_handler
from notifications.manager import NotificationManager
from shared.config import get_config

def setup_test_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def test_config_loading():
    """Test configuration loading"""
    print("\n=== Testing Configuration Loading ===")
    try:
        config = get_config()
        print(f"✓ Configuration loaded successfully")
        print(f"  - Schoology URL: {config.schoology.base_url}")
        print(f"  - AWS Region: {config.aws.region}")
        print(f"  - DynamoDB Table: {config.aws.dynamodb_table_name}")
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False

def test_scraper_component():
    """Test scraper component initialization"""
    print("\n=== Testing Scraper Component ===")
    try:
        scraper = GradeScraper()
        
        # Test driver initialization
        init_success = scraper.initialize_driver()
        if init_success:
            print("✓ Scraper driver initialized successfully")
            scraper.cleanup()
            return True
        else:
            print("✗ Scraper driver initialization failed")
            return False
            
    except Exception as e:
        print(f"✗ Scraper component test failed: {e}")
        return False

def test_comparator_component():
    """Test comparator component"""
    print("\n=== Testing Comparator Component ===")
    try:
        comparator = GradeComparator()
        
        # Test with dummy data
        test_data = {"test": "data", "timestamp": "2023-01-01"}
        changes = comparator.detect_changes(test_data)
        
        print(f"✓ Comparator component initialized successfully")
        if changes:
            print(f"  - Changes detected (expected for test): {changes['type']}")
        else:
            print(f"  - No changes detected")
        
        return True
        
    except Exception as e:
        print(f"✗ Comparator component test failed: {e}")
        return False

def test_notification_providers():
    """Test notification providers"""
    print("\n=== Testing Notification Providers ===")
    try:
        notifier = GradeNotifier()
        
        if notifier.notification_manager:
            available_providers = notifier.get_available_providers()
            print(f"✓ Notification manager initialized")
            print(f"  - Available providers: {available_providers}")
            
            # Test provider availability
            test_results = notifier.test_notifications()
            for provider, status in test_results.items():
                status_symbol = "✓" if status else "✗"
                print(f"  - {provider}: {status_symbol}")
            
            return len(available_providers) > 0
        else:
            print("✗ No notification manager available")
            return False
            
    except Exception as e:
        print(f"✗ Notification provider test failed: {e}")
        return False

def test_pipeline_status():
    """Test pipeline status and component integration"""
    print("\n=== Testing Pipeline Status ===")
    try:
        pipeline = GradePipeline()
        
        # Get pipeline status
        status = pipeline.get_pipeline_status()
        print("✓ Pipeline status retrieved:")
        for key, value in status.items():
            print(f"  - {key}: {value}")
        
        # Test component testing
        component_results = pipeline.test_pipeline_components()
        print("\n✓ Component test results:")
        for component, result in component_results.items():
            status_symbol = "✓" if result else "✗"
            print(f"  - {component}: {status_symbol}")
        
        return True
        
    except Exception as e:
        print(f"✗ Pipeline status test failed: {e}")
        return False

def test_error_handling():
    """Test error handling system"""
    print("\n=== Testing Error Handling ===")
    try:
        # Clear any existing errors
        error_handler.clear_error_history()
        
        # Test error logging
        from pipeline.error_handling import handle_scraping_error, ErrorSeverity
        
        test_error = Exception("Test error for validation")
        pipeline_error = handle_scraping_error(test_error, {"test": True})
        
        # Check error summary
        error_summary = error_handler.get_error_summary()
        
        print("✓ Error handling system working:")
        print(f"  - Total errors: {error_summary['total_errors']}")
        print(f"  - By severity: {error_summary['by_severity']}")
        print(f"  - By component: {error_summary['by_component']}")
        
        # Clear test error
        error_handler.clear_error_history()
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def run_integration_test():
    """Run a lightweight integration test (no actual scraping)"""
    print("\n=== Running Integration Test ===")
    try:
        pipeline = GradePipeline()
        
        # Test pipeline without actually running scraping
        print("✓ Pipeline created successfully")
        
        # Check if all components are properly wired
        scraper_ready = pipeline.scraper is not None
        comparator_ready = pipeline.comparator is not None
        notifier_ready = pipeline.notifier is not None
        data_service_ready = pipeline.data_service is not None
        
        print(f"  - Scraper component: {'✓' if scraper_ready else '✗'}")
        print(f"  - Comparator component: {'✓' if comparator_ready else '✗'}")
        print(f"  - Notifier component: {'✓' if notifier_ready else '✗'}")
        print(f"  - Data service component: {'✓' if data_service_ready else '✗'}")
        
        all_ready = all([scraper_ready, comparator_ready, notifier_ready, data_service_ready])
        
        if all_ready:
            print("✓ All pipeline components properly integrated")
        else:
            print("✗ Some pipeline components not properly integrated")
        
        return all_ready
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    setup_test_logging()
    print("=== Phase 3 Pipeline Testing ===")
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Scraper Component", test_scraper_component),
        ("Comparator Component", test_comparator_component),
        ("Notification Providers", test_notification_providers),
        ("Pipeline Status", test_pipeline_status),
        ("Error Handling", test_error_handling),
        ("Integration Test", run_integration_test),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 3 pipeline is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())