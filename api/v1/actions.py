import flask
from api.session import BIND_MAIN_DB

blueprint = flask.Blueprint('v1', __name__, url_prefix='/v1/<tenant>')


@blueprint.route('/')
def index():
    session = flask.current_app.db_session()
    return 'index'