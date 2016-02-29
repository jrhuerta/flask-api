from werkzeug.contrib.cache import (
    NullCache,
    RedisCache,
    SimpleCache
)
import cPickle
import logging
from hashlib import sha256
from functools import wraps

_backend_factory = {
    'null': NullCache,
    'redis': RedisCache,
    'simple': SimpleCache
}
_backend_config = {}

serializer = cPickle
hash_func = sha256


def configure(config={}):
    for name in _backend_factory:
        if name in config:
            _backend_config[name] = config.get(name)


class Cache(object):

    def __init__(self, backend='null', expire=None):
        self.expire = expire or self.expire
        cache_factory = _backend_factory.get(backend)
        if not cache_factory:
            cache_factory = NullCache
            logging.info('%s: not configured defaulting to null cache'
                         .format(backend))
        cache_config = _backend_config.get(backend, {})
        cache_config.update(dict(expire=expire))
        self.cache = cache_factory(**cache_config)

    def default_make_key(self, fname, prefix=None, *args, **kwargs):
        return '_'.join(filter(None, [
            prefix() if callable(prefix) else prefix,
            fname,
            hash_func(serializer.dumps((args, kwargs))).hexdigest()
        ]))

    def memoize(self, expire=None, unless=None):

        def decorator(f):

            @wraps(f)
            def wrapper(*args, **kwargs):
                key = self.make_key(f.__name__, *args, **kwargs)
                value = None
                if not unless() if callable(unless) else unless:
                    try:
                        value = self.cache.get(key)
                    except Exception, e:
                        logging.error(e.message)
                if not value:
                    value = f(*args, **kwargs)
                try:
                    self.cache.set(key, value, expire=expire)
                except Exception, e:
                    logging.error(e.message)
                return value

            return wrapper

        return decorator

