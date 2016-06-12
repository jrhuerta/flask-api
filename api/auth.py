from flask import current_app, g, request


CONST_SESSION_HEADER = 'PHPSESSID'


def get_php_session():
    session = request.headers.get(CONST_SESSION_HEADER) or \
              request.cookies.get(CONST_SESSION_HEADER)
    return session


def get_current_user():
    session_id = get_php_session()
    if session_id:
        user = get_user_by_session_id(session_id)

    if not user and request.authorization:
        username = request.authorization.username
        user = get_user_by_username(username)
        if not user:
            user = get_api_user(username)
    return user


def current_user():
    with current_app.request_context():
        user = g.current_user
        if not user:
            user = g._current_user = get_current_user()
        return user