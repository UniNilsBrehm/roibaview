# plugins/loader.py
import importlib.util
import os
import inspect
from roibaview.plugins.base import BasePlugin


def load_plugins(context=None):
    plugin_dir = os.path.dirname(__file__)
    plugins = []

    for fname in os.listdir(plugin_dir):
        if fname.endswith(".py") and fname not in {"__init__.py", "base.py", "loader.py"}:
            path = os.path.join(plugin_dir, fname)
            spec = importlib.util.spec_from_file_location(fname[:-3], path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"Error loading plugin {fname}: {e}")
                continue

            # Find plugin classes
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    try:
                        try:
                            plugin = obj(**context) if context else obj()
                            plugins.append(plugin)
                        except Exception as e:
                            print(f"Failed to instantiate plugin {obj.__name__}: {e}")
                    except Exception as e:
                        print(f"Failed to instantiate plugin {obj.__name__}: {e}")
    return plugins
