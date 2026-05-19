from re import fullmatch

from zenlib.logging import ClassLogger
from zenlib.util import colorize as c_
from .shared import METRIC_NAME_REGEX


class Labels(ClassLogger, dict):
    """A dictionary of labels, used by both Metrics and Exporters"""

    def __init__(self, dict_items={}, **kwargs) -> None:
        """Create a new Labels object from a dictionary"""
        super().__init__(**kwargs)
        self.update(dict_items)

    def __setitem__(self, key: str, value: str) -> None:
        self._check_label(key, value)
        super().__setitem__(key, value)

    def update(self, new_labels):
        """Updates the labels with the new labels"""
        for key, value in new_labels.items():
            self[key] = value
            self.logger.debug(f"Added label {c_(key, 'green')}={c_(value, 'blue')}")

    def _check_label(self, name: str, value: str) -> None:
        """Check that the label name and value are valid.
        https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels

        The label must start with a letter or an underscore, followed by letters, numbers or underscores.
        The value can be any unicode string, but it cannot be empty."""
        if not isinstance(name, str):
            raise TypeError(f"Label name must be a string, got: {c_(type(name).__name__, 'red')} ({name})")

        # Check that the label name is valid
        if not fullmatch(METRIC_NAME_REGEX, name):
            raise ValueError(f"Invalid label name: {c_(name, 'red')}. Label names must match the regex: {METRIC_NAME_REGEX}")

        # Check that the label value is a string
        if not isinstance(value, str):
            raise TypeError(f"[{c_(name, 'blue')}] Label value must be a string, got: {c_(type(value).__name__, 'red')} ({value})")

        if not value:
            raise ValueError(f"Label value cannot be empty: {c_(name, 'red')}")

    def __str__(self) -> str:
        return ",".join(['%s="%s"' % (name, value) for name, value in self.items()])

    def copy(self) -> "Labels":
        """Returns a copy of the labels"""
        return Labels(super().copy(), logger=self.logger.parent)
