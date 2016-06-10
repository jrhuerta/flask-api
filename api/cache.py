import time


def memoize(timeout=300):
    """ Memoize decorator for pure functions using a dict
    :param timeout: Key expire time (in seconds)
    """
    def decorator(f):
        class memodict(dict):

            def __init__(self, f):
                self.timeout = timeout
                self.func = f

            def __call__(self, *args):
                timestamp, value = self[args]
                if value and timeout is not None and time.time() - timestamp > self.timeout:
                    _, value = self.__missing__(args)
                return value

            def __missing__(self, key):
                ret = self[key] = (time.time(), self.func(*key))
                return ret

        return memodict(f)
    return decorator
