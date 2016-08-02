from flask import _app_ctx_stack as stack
import logging
import sqlalchemy
from sqlalchemy import exc
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import scoped_session, sessionmaker

from api.cache import memoize

__all__ = [
    'create_engine',
    'session_factory',
    'teardown'
]

_CONST_CTX_SESSION = '_sqlalchemy_scoped_sessions'


class LookLively(object):
    """Ensures that MySQL connections checked out of the pool are alive."""
    def checkout(self, dbapi_con, con_record, con_proxy):
        try:
            try:
                dbapi_con.ping(False)
            except TypeError:
                dbapi_con.ping()
            except AttributeError:
                # If it's not a mysql connection just skip
                return
        except dbapi_con.OperationalError as ex:
            if ex.args[0] in (2006, 2013, 2014, 2045, 2055):
                raise exc.DisconnectionError()
            else:
                raise


@memoize
def create_engine(url, **kwargs):
    default_params = {
        'encoding': 'utf8',
        'echo': False,
        'listeners': [LookLively()]
    }
    engine_type_params = {
        'mysql': {'pool_recycle': 3600}
    }
    dialect = make_url(url).get_dialect()
    params = default_params
    if dialect in engine_type_params:
        params.update(engine_type_params[dialect])
    params.update(kwargs)
    return sqlalchemy.create_engine(url, **params)


def create_session(url):
    assert url, 'Connection string required.'
    engine = create_engine(url)
    session = scoped_session(
        sessionmaker(bind=engine, autocommit=False, autoflush=True),
        scopefunc=stack.__ident_func__
    )
    logging.debug('Session created: {}'.format(url))
    return session


def session_factory(tenant, db):
    ctx = stack.top
    assert ctx is not None, 'Requesting a session with no context.'
    sessions = getattr(ctx, _CONST_CTX_SESSION, None)
    if sessions is None:
        sessions = {}
        setattr(ctx, _CONST_CTX_SESSION, sessions)
    db_session = sessions.get(db)
    if not db_session:
        tenant_ = tenant() if callable(tenant) else tenant
        url = getattr(tenant_, db, None)
        assert url, '{0}: Not configured for {1}'.format(db, tenant_)
        db_session = create_session(url)
        sessions[db] = db_session
    return db_session


def teardown(exception):
    ctx = stack.top
    sessions = getattr(ctx, _CONST_CTX_SESSION, None)
    if not sessions:
        return exception
    for db, session in sessions.items():
        if exception is None:
            try:
                session.commit()
            except Exception as ex:
                exception = ex
                logging.error('ERROR: ' + ex.message)
        logging.debug('{}: Remove session.' .format(db))
        session.remove()
    return exception
