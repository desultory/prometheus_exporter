class CachedExporter:
    """
    Decorated exporter class.
    Adds caching to the get_metrics function.
    Default cache life is 60 seconds.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cache_life := kwargs.pop('cache_life', None):
            self.cache_life = cache_life
        elif not hasattr(self, 'cache_life'):
            self.cache_life = 60

    def __setattr__(self, name, value):
        """ Override setattr for cache_life """
        if name == "cache_life":
            if not isinstance(value, int):
                raise TypeError("cache_life must be an integer")
            if value < 0:
                raise ValueError("cache_life must be a positive integer")
            self.logger.info("Setting cache_life to: %ds", value)
        super().__setattr__(name, value)

    def read_config(self):
        """ Override read_config to add cache_life """
        super().read_config()
        if 'cache_life' in self.config:
            self.cache_life = self.config['cache_life']

    async def _get_metrics(self):
        return self._cached_metrics if hasattr(self, '_cached_metrics') else await super()._get_metrics()

    async def get_metrics(self, label_filter={}):
        """ Get metrics from the exporter, caching the result. """
        from time import time
        cache_time = time() - getattr(self, '_cache_time', 0)
        self.logger.debug("Cache time: %d" % (cache_time))
        if not hasattr(self, '_cached_metrics') or cache_time >= self.cache_life:
            self._cached_metrics = await super().get_metrics(label_filter=label_filter)
            self._cache_time = time()
        else:
            self.logger.info("Returning cached metrics.")
            self.logger.debug("Cached metrics: %s", self._cached_metrics)
        return await self.filter_metrics(label_filter=label_filter)
