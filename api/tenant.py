import logging
from sqlalchemy import (
    create_engine,
    Column,
    Boolean,
    Integer,
    Unicode
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import exc, scoped_session, sessionmaker

_Base = declarative_base()


class _Tenant(_Base):
    """Tenant table mapping."""
    __tablename__ = 'tbl_sys_tenants'
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    domain = Column(Unicode(255), nullable=False)
    tenant = Column(Unicode(255), nullable=False, unique=True, index=True)
    mysql = Column('mysql_dsn', Unicode(255), nullable=False)
    mongo = Column('mongo_dsn', Unicode(255), nullable=False)
    clinical = Column('clinical_dsn', Unicode(255), nullable=False)
    intake = Column('intake_dsn', Unicode(255), nullable=False)
    disabled = Column(Boolean, nullable=False, default=0, server_default='0')


def get_tenant(tenant_db_url, name):
    engine = create_engine(tenant_db_url)
    tenant_name = name() if callable(name) else name
    session = None
    try:
        session = scoped_session(sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=True
        ))
        tenant = session \
            .query(_Tenant) \
            .filter(_Tenant.tenant == tenant_name) \
            .one_or_none()

        # No configuration found for this tenant.
        assert tenant, 'Tenant not configured.'
        assert not tenant.disabled, '{0}: Tenant disabled.'.format(tenant)

        logging.debug('{}: Tenant found'.format(name))
        return tenant
    except exc.MultipleResultsFound:
        # Multiple configurations found.
        raise AssertionError('{}: Multiple configurations found'.format(name))
    finally:
        if session is not None:
            session.remove()
            logging.debug('Finalizing tenant session.')
