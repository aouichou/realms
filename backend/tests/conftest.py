"""
Pytest configuration and shared fixtures
"""


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that make real API calls",
    )


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires --integration flag)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
