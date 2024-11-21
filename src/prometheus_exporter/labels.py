from re import fullmatch

from zenlib.logging import ClassLogger
from .shared import METRIC_NAME_REGEX


class Labels(ClassLogger, dict):
    """A dictionary of labels, used by both Metrics and Exporters"""

    def __init__(self, dict_items={}, **kwargs):
        """Create a new Labels object from a dictionary"""
        super().__init__(**kwargs)
        self.update(dict_items)

    def __setitem__(self, key, value):
        self._check_label(key, value)
        super().__setitem__(key, value)

    def update(self, new_labels):
        """Updates the labels with the new labels"""
        for key, value in new_labels.items():
            self[key] = value
            self.logger.debug("Added label %s=%s", key, value)

    def _check_label(self, name: str, value: str):
        """Check that the label name and value are valid.
        https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels

        The label must start with a letter or an underscore, followed by letters, numbers or underscores.
        The value can be any unicode string, but it cannot be empty."""
        if not isinstance(name, str):
            raise TypeError("Label names must be strings")

        # Check that the label name is valid
        if not fullmatch(METRIC_NAME_REGEX, name):
            raise ValueError("Invalid label name: %s" % name)

        # Check that the label value is a string
        if not isinstance(value, str):
            raise TypeError("Label values must be strings")

        if not value:
            raise ValueError("Label values cannot be empty")

    def __str__(self):
        return ",".join(['%s="%s"' % (name, value) for name, value in self.items()])

    def copy(self):
        """Returns a copy of the labels"""
        return Labels(super().copy(), logger=self.logger.parent)
