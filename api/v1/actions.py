import flask

blueprint = flask.Blueprint('v1', __name__, url_prefix='/v1/<tenant>')


@blueprint.route('/')
def index():
    session = flask.current_app.session_factory('mysql')
    return 'index'