# plugins/base.py

class BasePlugin:
    """
    Abstract base class for all RoiBaView plugins.
    """
    name = "Unnamed Plugin"
    category = "filter"  # 'filter', 'tool', 'analysis', etc.
    unavailable_reason = "This plugin is unavailable."

    @classmethod
    def available(cls):
        """
        Optional method to determine if the plugin should be loaded.
        Override in subclasses if conditional loading is needed.
        """
        return True

    def apply(self, data=None, sampling_rate=None):
        """
        Apply the plugin logic.

        For 'filter' plugins, both parameters are used.
        For 'tool' plugins, these can be ignored.

        Parameters:
            data (np.ndarray): ROI data (optional for tools)
            sampling_rate (float): Sampling rate (Hz)

        Returns:
            np.ndarray or None: Processed data or nothing
        """
        raise NotImplementedError("Plugin must implement the 'apply' method.")