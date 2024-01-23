import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def retry(times, exception_cls=Exception, timeout: Optional[int] = 10) -> Callable:
    def outer(func) -> Callable:
        def inner(*args, **kwargs):
            count = times
            while count:
                try:
                    return func(*args, **kwargs)
                except exception_cls as e:
                    logger.warning(f"Failed executing function '{str(func)}': {str(e)}")
                    count -= 1
                    if not count:
                        raise e
                    if timeout:
                        time.sleep(timeout)

        return inner

    return outer
