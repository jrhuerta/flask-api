import json
import pytest
from flask import _app_ctx_stack as stack

from api.api import (
    ApiException,
    get_tenant_name,
    handle_api_errors,
    handle_assertion_errors
)


@pytest.yield_fixture
def request(app):
    with app.test_request_context():
        yield app


def test_handle_api_errors(request):
    api_error = ApiException('Test api error.')
    response = handle_api_errors(api_error)
    assert response
    assert response.status_code == 400
    assert response.mimetype == 'application/json'
    data = json.loads(response.data.decode('utf-8'))
    assert data.get('message') == api_error.message
    assert data.get('status_code') == api_error.status_code


def test_handle_api_errors_status_code_and_payload(request):
    custom_api_error = ApiException(
        'Custom api error with payload',
        status_code=403, payload={'payload': 'precious'})
    response = handle_api_errors(custom_api_error)
    assert response
    data = json.loads(response.data.decode('utf-8'))
    assert data.get('status_code') == custom_api_error.status_code
    assert data.get('payload') == custom_api_error.payload.get('payload')


def test_handle_assertion_errors(request):
    assert_error = AssertionError('Assertion message.')
    response = handle_assertion_errors(assert_error)
    assert response
    assert response.status_code == 400
    assert response.mimetype == 'application/json'
    data = json.loads(response.data.decode('utf-8'))
    assert data.get('message') == "{}".format(assert_error)
    assert data.get('status_code') == response.status_code


def test_get_tenant_name_no_context():
    with pytest.raises(AssertionError):
        get_tenant_name()


def tes_get_tenant_name_no_tenant():
    assert not get_tenant_name()


def test_get_tenant_name(request):
    context = stack.top
    context.tenant = 'tenant'
    assert get_tenant_name() == 'tenant'

