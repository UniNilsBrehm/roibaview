# plugins/loader.py
import importlib.util
import os
import inspect
from roibaview.plugins.base import BasePlugin

def load_plugins():
    plugin_dir = os.path.join(os.path.dirname(__file__))
    plugins = []
    for fname in os.listdir(plugin_dir):
        if fname.endswith(".py") and fname not in ["__init__.py", "base.py", "loader.py"]:
            path = os.path.join(plugin_dir, fname)
            spec = importlib.util.spec_from_file_location(fname[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for name, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, BasePlugin) and cls is not BasePlugin:
                    plugins.append(cls())
    return plugins