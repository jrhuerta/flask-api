from flask import _app_ctx_stack as stack
import logging
from sqlalchemy import exc
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import scoped_session, sessionmaker


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
        except dbapi_con.OperationalError, ex:
            if ex.args[0] in (2006, 2013, 2014, 2045, 2055):
                raise exc.DisconnectionError()
            else:
                raise


def create_engine(url, **kwargs):
    default_params = dict(
        encoding='utf8',
        echo=False,
        listeners=[LookLively()]
    )
    engine_type_params = dict(
        mysql=dict(pool_recycle=3600)
    )
    dialect = make_url(url).get_dialect()
    params = default_params
    if dialect in engine_type_params:
        params.update(engine_type_params[dialect])
    params.update(kwargs)
    return sqlalchemy_create_engine(url, **params)


def create_session(url):
    assert url, "Connection string required."
    engine = create_engine(url)
    session = scoped_session(
        sessionmaker(bind=engine, autocommit=False, autoflush=True),
        scopefunc=stack.__ident_func__
    )
    logging.debug("Session created: {}".format(url))
    return session


def session_factory(tenant, db):
    ctx = stack.top
    assert ctx is not None, "Requesting a session with no context."
    sessions = getattr(ctx, _CONST_CTX_SESSION, None)
    if sessions is None:
        sessions = {}
        setattr(ctx, _CONST_CTX_SESSION, sessions)
    db_session = sessions.get(db)
    if not db_session:
        tenant_ = tenant() if callable(tenant) else tenant
        url = getattr(tenant_, db, None)
        db_session = create_session(url)
        sessions[db] = db_session
    return db_session


def teardown(exception):
    ctx = stack.top
    sessions = getattr(ctx, _CONST_CTX_SESSION, None)
    if not sessions:
        return exception
    for db, session in sessions.iteritems():
        if exception is None:
            try:
                session.commit()
            except Exception, ex:
                exception = ex
                logging.error("ERROR: " + ex.message)
        logging.debug("Remove session: {}" .format(str(session.bind.url)))
        session.remove()
    return exception
