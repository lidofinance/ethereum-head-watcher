import functools
import threading


def thread_as_daemon(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> threading.Thread:
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
        return t

    return wrapper
