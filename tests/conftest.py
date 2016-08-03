import pytest

import main


@pytest.yield_fixture
def app():
    with main.app.app_context():
        yield main.app
