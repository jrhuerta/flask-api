from flask import Flask,  jsonify, _app_ctx_stack as stack
from functools import partial

import api.session as session
import api.tenant as tenant


from api.v1.actions import blueprint


def app_factory(name, config=None):
    app = Flask(name)
    app.config.update(config or {})

    app.errorhandler(ApiException)(handle_api_errors)
    app.errorhandler(AssertionError)(handle_assertion_errors)

    get_tenant_for_request = partial(
        tenant.get_tenant,
        app.config.get('TENANT_DSN'),
        get_tenant_name)

    app.session_factory = partial(
        session.session_factory,
        get_tenant_for_request)

    app.teardown_appcontext(session.teardown)

    app.url_value_preprocessor(pull_tenant_from_request)

    # loop through blueprints in config and load them
    app.register_blueprint(blueprint)

    return app


class ApiException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv.update(status_code=self.status_code, message=self.message)
        return rv


def handle_api_errors(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def handle_assertion_errors(error):
    api_error = ApiException("{}".format(error), status_code=400)
    return handle_api_errors(api_error)


def pull_tenant_from_request(endpoint, values):
    assert stack.top, 'Outside application context.'
    context = stack.top
    context.tenant = values.pop('tenant', None) if values else None


def get_tenant_name():
    assert stack.top, 'Outside application context.'
    context = stack.top
    return getattr(context, 'tenant', None)


