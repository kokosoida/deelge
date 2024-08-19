import json
import pickle
from functools import wraps
from pathlib import Path

CACHE_DIR = Path(__file__).parent / '.cache'

def cache_in_file(f):
    """Decorator to cache the results of a function call in file with pickle."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = f"{sorted(args)}{sorted(kwargs.items())}"
        cache_file = CACHE_DIR / f"{f.__name__}_{key}.pkl"
        if cache_file.exists():
            with open(cache_file, 'rb') as file:
                return pickle.load(file)

        result = f(*args, **kwargs)

        CACHE_DIR.mkdir(exist_ok=True)
        with open(cache_file, 'wb') as file:
            pickle.dump(result, file)

        return result

    return wrapper


def set_and_get(key, value=None):
    """Set a value in the cache or get it if it already exists."""
    key = f"set_and_get_{key}.pkl"
    cache_file = CACHE_DIR / key
    prev_value = None

    if cache_file.exists():
        with open(cache_file, 'rb') as file:
            prev_value = pickle.load(file)

    with open(cache_file, 'wb') as file:
        pickle.dump(value, file)

    return prev_value
