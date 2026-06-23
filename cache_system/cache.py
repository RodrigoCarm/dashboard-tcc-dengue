from cachetools import TTLCache
from threading import Lock

class CacheConfig():
    def __init__(self, horas: int = 24):
        self.cache_sistem = TTLCache(maxsize=10, ttl=60*60*horas)
        self.cache_lock = Lock()

    def get_cache(self, key: str):
        with self.cache_lock:
            return self.cache_sistem.get(key)    
    
    def set_cache(self, key: str, value):
        with self.cache_lock:
            self.cache_sistem[key] = value
