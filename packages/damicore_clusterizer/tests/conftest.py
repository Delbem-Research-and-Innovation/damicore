import pytest


@pytest.fixture
def sample_input() -> list[float]:
    """Provide sample data for clusterizer tests."""
    return [1.0, 2.0, 3.0]
