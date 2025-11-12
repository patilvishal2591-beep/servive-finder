"""
Custom test runner and utilities for ServiceFinder application.
Provides enhanced test running capabilities and coverage reporting.
"""

import os
import sys
from django.test.runner import DiscoverRunner
from django.conf import settings
from django.core.management import call_command
from io import StringIO


class ServiceFinderTestRunner(DiscoverRunner):
    """
    Custom test runner for ServiceFinder application.
    Provides enhanced test running with coverage reporting.
    """
    
    def __init__(self, *args, **kwargs):
        self.coverage = None
        self.coverage_report = kwargs.pop('coverage_report', True)
        super().__init__(*args, **kwargs)
    
    def setup_test_environment(self, **kwargs):
        """Set up test environment with coverage if enabled"""
        super().setup_test_environment(**kwargs)
        
        if self.coverage_report:
            try:
                import coverage
                self.coverage = coverage.Coverage(
                    source=['usermgmt', 'servicemgmt'],
                    omit=[
                        '*/migrations/*',
                        '*/tests/*',
                        '*/venv/*',
                        '*/env/*',
                        'manage.py',
                        '*/settings/*',
                        '*/wsgi.py',
                        '*/asgi.py',
                    ]
                )
                self.coverage.start()
            except ImportError:
                print("Coverage.py not installed. Install with: pip install coverage")
                self.coverage = None
    
    def teardown_test_environment(self, **kwargs):
        """Tear down test environment and generate coverage report"""
        super().teardown_test_environment(**kwargs)
        
        if self.coverage:
            self.coverage.stop()
            self.coverage.save()
            
            # Generate coverage report
            print("\n" + "="*50)
            print("COVERAGE REPORT")
            print("="*50)
            self.coverage.report()
            
            # Generate HTML coverage report
            html_dir = os.path.join(settings.BASE_DIR, 'htmlcov')
            self.coverage.html_report(directory=html_dir)
            print(f"\nHTML coverage report generated in: {html_dir}")
    
    def run_tests(self, test_labels, **kwargs):
        """Run tests with enhanced reporting"""
        print("="*50)
        print("SERVICEFINDER TEST SUITE")
        print("="*50)
        
        if not test_labels:
            test_labels = [
                'usermgmt.tests',
                'servicemgmt.tests',
                'tests.integration',
                'tests.frontend'
            ]
        
        print(f"Running tests: {', '.join(test_labels)}")
        print("-"*50)
        
        result = super().run_tests(test_labels, **kwargs)
        
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        
        return result


class TestDataManager:
    """
    Utility class for managing test data across test suites.
    """
    
    @staticmethod
    def create_test_database():
        """Create and populate test database with sample data"""
        from tests.utils.factories import TestDataFactory
        
        print("Creating test database with sample data...")
        
        # Create multiple complete scenarios
        scenarios = []
        for i in range(3):
            scenario = TestDataFactory.create_complete_booking_scenario()
            scenarios.append(scenario)
        
        # Create multiple providers scenario
        providers_scenario = TestDataFactory.create_multiple_providers_scenario(count=10)
        
        print(f"Created {len(scenarios)} complete booking scenarios")
        print(f"Created {len(providers_scenario['providers'])} providers with {len(providers_scenario['services'])} services")
        
        return {
            'booking_scenarios': scenarios,
            'providers_scenario': providers_scenario
        }
    
    @staticmethod
    def cleanup_test_data():
        """Clean up test data after tests"""
        from django.contrib.auth import get_user_model
        from usermgmt.models import ServiceCategory, ProviderService
        from servicemgmt.models import ServiceBooking, Review, Payment, Notification
        
        User = get_user_model()
        
        # Clean up in reverse dependency order
        Notification.objects.all().delete()
        Payment.objects.all().delete()
        Review.objects.all().delete()
        ServiceBooking.objects.all().delete()
        ProviderService.objects.all().delete()
        ServiceCategory.objects.all().delete()
        User.objects.all().delete()
        
        print("Test data cleaned up successfully")


class TestMetrics:
    """
    Utility class for collecting and reporting test metrics.
    """
    
    def __init__(self):
        self.metrics = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'test_categories': {
                'unit_tests': 0,
                'integration_tests': 0,
                'frontend_tests': 0
            },
            'coverage_percentage': 0,
            'execution_time': 0
        }
    
    def update_metrics(self, test_result):
        """Update metrics based on test results"""
        self.metrics['total_tests'] = test_result.testsRun
        self.metrics['failed_tests'] = len(test_result.failures) + len(test_result.errors)
        self.metrics['passed_tests'] = self.metrics['total_tests'] - self.metrics['failed_tests']
        
        if hasattr(test_result, 'skipped'):
            self.metrics['skipped_tests'] = len(test_result.skipped)
    
    def categorize_tests(self, test_labels):
        """Categorize tests by type"""
        for label in test_labels:
            if 'integration' in label:
                self.metrics['test_categories']['integration_tests'] += 1
            elif 'frontend' in label:
                self.metrics['test_categories']['frontend_tests'] += 1
            else:
                self.metrics['test_categories']['unit_tests'] += 1
    
    def generate_report(self):
        """Generate comprehensive test metrics report"""
        report = []
        report.append("="*60)
        report.append("TEST METRICS REPORT")
        report.append("="*60)
        report.append(f"Total Tests Run: {self.metrics['total_tests']}")
        report.append(f"Passed: {self.metrics['passed_tests']}")
        report.append(f"Failed: {self.metrics['failed_tests']}")
        report.append(f"Skipped: {self.metrics['skipped_tests']}")
        report.append("")
        report.append("Test Categories:")
        report.append(f"  Unit Tests: {self.metrics['test_categories']['unit_tests']}")
        report.append(f"  Integration Tests: {self.metrics['test_categories']['integration_tests']}")
        report.append(f"  Frontend Tests: {self.metrics['test_categories']['frontend_tests']}")
        report.append("")
        
        if self.metrics['coverage_percentage'] > 0:
            report.append(f"Code Coverage: {self.metrics['coverage_percentage']:.1f}%")
        
        if self.metrics['execution_time'] > 0:
            report.append(f"Execution Time: {self.metrics['execution_time']:.2f} seconds")
        
        report.append("="*60)
        
        return "\n".join(report)


def run_specific_test_suite(suite_name):
    """
    Run a specific test suite by name.
    
    Args:
        suite_name (str): Name of the test suite ('unit', 'integration', 'frontend', 'all')
    """
    test_mapping = {
        'unit': ['usermgmt.tests', 'servicemgmt.tests'],
        'integration': ['tests.integration'],
        'frontend': ['tests.frontend'],
        'all': ['usermgmt.tests', 'servicemgmt.tests', 'tests.integration', 'tests.frontend']
    }
    
    if suite_name not in test_mapping:
        print(f"Invalid test suite: {suite_name}")
        print(f"Available suites: {', '.join(test_mapping.keys())}")
        return False
    
    test_labels = test_mapping[suite_name]
    
    print(f"Running {suite_name} test suite...")
    print(f"Test labels: {', '.join(test_labels)}")
    
    # Use Django's call_command to run tests
    call_command('test', *test_labels, verbosity=2)
    
    return True


def generate_test_coverage_report():
    """
    Generate a comprehensive test coverage report in markdown format.
    """
    try:
        import coverage
        
        # Load coverage data
        cov = coverage.Coverage()
        cov.load()
        
        # Generate report
        output = StringIO()
        cov.report(file=output)
        coverage_text = output.getvalue()
        
        # Create markdown report
        markdown_report = []
        markdown_report.append("# Test Coverage Report")
        markdown_report.append("")
        markdown_report.append("## Summary")
        markdown_report.append("")
        markdown_report.append("```")
        markdown_report.append(coverage_text)
        markdown_report.append("```")
        markdown_report.append("")
        markdown_report.append("## Test Categories")
        markdown_report.append("")
        markdown_report.append("### Unit Tests")
        markdown_report.append("- User Management Tests")
        markdown_report.append("- Service Management Tests")
        markdown_report.append("- Authentication Tests")
        markdown_report.append("- Permission Tests")
        markdown_report.append("")
        markdown_report.append("### Integration Tests")
        markdown_report.append("- Booking Workflow Tests")
        markdown_report.append("- Geolocation Integration Tests")
        markdown_report.append("- Notification System Tests")
        markdown_report.append("- Payment Processing Tests")
        markdown_report.append("")
        markdown_report.append("### Frontend Tests")
        markdown_report.append("- Template View Tests")
        markdown_report.append("- Form Validation Tests")
        markdown_report.append("- Responsive Design Tests")
        markdown_report.append("- JavaScript Functionality Tests")
        markdown_report.append("")
        markdown_report.append("## Coverage Details")
        markdown_report.append("")
        markdown_report.append("The test suite covers:")
        markdown_report.append("- ✅ User authentication and authorization")
        markdown_report.append("- ✅ Service listing and management")
        markdown_report.append("- ✅ Booking workflow (create, confirm, complete, cancel)")
        markdown_report.append("- ✅ Payment processing (fake gateway)")
        markdown_report.append("- ✅ Review and rating system")
        markdown_report.append("- ✅ Geolocation-based search")
        markdown_report.append("- ✅ Notification system")
        markdown_report.append("- ✅ Role-based access control")
        markdown_report.append("- ✅ Template rendering and frontend functionality")
        markdown_report.append("- ✅ Form validation and error handling")
        markdown_report.append("")
        
        return "\n".join(markdown_report)
        
    except ImportError:
        return "Coverage.py not installed. Install with: pip install coverage"
    except Exception as e:
        return f"Error generating coverage report: {str(e)}"


if __name__ == "__main__":
    """
    Command-line interface for running tests.
    Usage: python test_runner.py [suite_name]
    """
    if len(sys.argv) > 1:
        suite_name = sys.argv[1]
        run_specific_test_suite(suite_name)
    else:
        print("Usage: python test_runner.py [unit|integration|frontend|all]")
