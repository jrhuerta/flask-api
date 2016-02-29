from flask import _app_ctx_stack as stack
import logging
from sqlalchemy import (
    create_engine,
    Boolean,
    Column,
    Integer,
    Unicode
)
from sqlalchemy import exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

__all__ = [
    'BIND_MAIN_DB',
    'BIND_INTAKE_DB',
    'BIND_CLINICAL_DB',
    'engine_factory',
    'session_factory',
    'teardown'
]

BIND_MAIN_DB = 'mysql_dsn'
BIND_CLINICAL_DB = 'clinical_dsn'
BIND_INTAKE_DB = 'clinical_dsn'

_CONST_CTX_SESSION = '_sqlalchemy_scoped_session'
_Base = declarative_base()


class _Tenant(_Base):
    """Tenant table mapping.
    This could evolve into a multiple rows per tenant key, value style
    and be mapped as a dictionary collection.
    It will remain like this for the time been to maintain compatibility
    """
    __tablename__ = 'tbl_sys_tenants'
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    domain = Column(Unicode(255), nullable=False)
    tenant = Column(Unicode(255), nullable=False, unique=True, index=True)
    mysql_dsn = Column(Unicode(255), nullable=False)
    mongo_dsn = Column(Unicode(255), nullable=False)
    clinical_dsn = Column(Unicode(255), nullable=False)
    intake_dsn = Column(Unicode(255), nullable=False)
    disabled = Column(Boolean, nullable=False, default=0, server_default='0')


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


def teardown(exception):
    ctx = stack.top
    session = getattr(ctx, _CONST_CTX_SESSION, None)
    if session is not None:
        if exception is None:
            try:
                session.commit()
            except Exception, ex:
                exception = ex
                logging.error("SQL_ERROR: " + ex.message)
        logging.debug("REMOVE_SESSION: %s" % str(session.bind.url))
        session.remove()
    return exception


def _create_engine(dsn, **kwargs):
    default_params = dict(
        encoding='utf8',
        echo=False,
        listeners=[LookLively()]
    )

    engine_type_params = {
        'mysql': {'pool_recycle': 3600}
    }

    engine_type = dsn.split(":")[0].split("+")[0]

    params = default_params
    if engine_type in engine_type_params:
        params.update(engine_type_params[engine_type])
    params.update(kwargs)

    return create_engine(dsn, **params)


def _get_tenant_dsn(dsn, tenant, bind):
    session = None
    try:
        session = scoped_session(sessionmaker(
            bind=_create_engine(dsn),
            autocommit=False,
            autoflush=True
        ))
        tenant_row = session\
            .query(_Tenant)\
            .filter(_Tenant.tenant == tenant)\
            .first()

        # No configuration found for this tenant.
        assert tenant_row, "Tenant not configured."
        assert not tenant_row.disabled, "Tenant configured, but disabled."

        # Configuration found, creating new engine.
        tenant_dsn = getattr(tenant_row, bind)
        return tenant_dsn
    finally:
        if session is not None:
            session.commit()
            session.remove()
            logging.debug('Finalizing tenant session.')


def engine_factory(tenants_dsn, tenant_name, bind, **kwargs):
    tenant = tenant_name() if callable(tenant_name) else tenant_name
    dsn = _get_tenant_dsn(tenants_dsn, tenant, bind)
    return _create_engine(dsn, **kwargs)


def session_factory(tenant_name, tenants_dsn=None, override_dsn=None,
                    bind=BIND_MAIN_DB, **kwargs):
    ctx = stack.top
    assert ctx is not None, "Requesting a session with no context."

    session = getattr(ctx, _CONST_CTX_SESSION, None)
    if session is None:
        if override_dsn:
            engine = _create_engine(override_dsn, **kwargs)
        else:
            engine = engine_factory(tenants_dsn, tenant_name, bind, **kwargs)
        session = scoped_session(
            sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=True),
            scopefunc=stack.__ident_func__)
        setattr(ctx, _CONST_CTX_SESSION, session)
        logging.debug("CREATE_SESSION: %s" % str(engine.url))
    return session
