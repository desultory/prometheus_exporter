from time import time

from .exporter import Exporter

def is_positive_number(func):
    def wrapper(self, value):
        if not isinstance(value, int) and not isinstance(value, float):
            raise TypeError("%s must be an integer or float", func.__name__)
        if value < 0:
            raise ValueError("%s must be a positive number", func.__name__)
        return func(self, value)
    return wrapper


def cached_exporter(cls):
    if not isinstance(cls, Exporter) and not issubclass(cls, Exporter):
        raise TypeError("cached_exporter decorator must be used on an Exporter")

    class CachedExporter(cls):
        """
        Decorated exporter class.
        Adds caching to the get_metrics function.
        Default cache life is 60 seconds.
        """

        def __init__(self, *args, **kwargs):
            """Call the super which reads the config.
            Prefer cache life setting from kwargs, then config, then default to 60 seconds.
            """
            super().__init__(*args, **kwargs)
            self.cache_life = kwargs.pop("cache_life", self.config.get("cache_life", 60))
            self.logger.info("Cache life set to: %d seconds", self.cache_life)

        @property
        def cache_life(self) -> int:
            return getattr(self, "_cache_life", 60)

        @cache_life.setter
        @is_positive_number
        def cache_life(self, value) -> None:
            self.logger.info("Setting cache_life to: %ds", value)
            self._cache_life = value

        @property
        def cache_time(self) -> int:
            return getattr(self, "_cache_time", 0)

        @cache_time.setter
        @is_positive_number
        def cache_time(self, value) -> None:
            self.logger.info("Setting cache_time to: %d", value)
            self._cache_time = value

        @property
        def cache_age(self) -> int:
            """ Returns the age of the cache """
            cache_age = time() - getattr(self, "_cache_time", 0)
            self.logger.debug("[%s] Cache age: %d" % (self.name, cache_age))
            return time() - getattr(self, "_cache_time", 0)

        async def get_metrics(self, label_filter=None) -> list:
            """Get metrics from the exporter, respecting label filters and caching the result."""
            label_filter = label_filter or {}

            if not hasattr(self, "_cached_metrics") or self.cache_age >= self.cache_life:
                if new_metrics := await super().get_metrics(label_filter=label_filter):
                    self.metrics = new_metrics
                    self._cached_metrics = new_metrics
                    self.cache_time = time()
                elif hasattr(self, "_cached_metrics"):
                    self.logger.warning("[%s] Exporter returned no metrics, returning cached metrics" % self.name)
                    self.metrics = self._cached_metrics
            else:
                self.logger.log(5, "[%s] Returning cached metrics: %s" % (self.name, self._cached_metrics))
                self.metrics = self._cached_metrics
            return self.metrics.copy()

    CachedExporter.__name__ = f"Cached{cls.__name__}"
    CachedExporter.__module__ = cls.__module__
    CachedExporter.__qualname__ = cls.__qualname__.replace(cls.__name__, CachedExporter.__name__)
    CachedExporter.__doc__ = cls.__doc__

    return CachedExporter
