# plugins/base.py
class BasePlugin:
    name = "BasePlugin"
    category = "filter"  # could be 'filter', 'analysis', 'visualization'

    def apply(self, data, sampling_rate):
        raise NotImplementedError("Plugin must implement 'apply'")
