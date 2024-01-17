"""
Labels dictionary, used by both Metrics and Exporters.

Each Labels dictionary only allows a label name to be set once.
Labels are added to the global labels dictionary, which is used by
the filter function in exporters.
"""

from zenlib.logging import ClassLogger


class Labels(ClassLogger, dict):
    """ A dictionary of labels, used by both Metrics and Exporters """
    global_labels = {}

    def __init__(self, dict_items={}, **kwargs):
        """ Create a new Labels object from a dictionary """
        super().__init__(**kwargs)
        self.update(dict_items)

    def __setitem__(self, key, value):
        self._check_label(key, value)
        super().__setitem__(key, value)
        self._update_global_labels(key, value)

    def _update_global_labels(self, key, value):
        """ Update the global labels with the labels in this dictionary """
        if key not in Labels.global_labels:
            Labels.global_labels[key] = [value]
        else:
            Labels.global_labels[key].append(value)

    def update(self, new_labels):
        """ Updates the labels with the new labels """
        for key, value in new_labels.items():
            self[key] = value
            self.logger.debug("Added label %s=%s", key, value)

    def _check_label(self, name: str, value: str):
        """ Check that the label name and value are valid """
        # Check that the label name is a string
        if not isinstance(name, str):
            raise TypeError('Label names must be strings')

        # Check that the label value is a string
        if not isinstance(value, str):
            raise TypeError('Label values must be strings')

    def __str__(self):
        return ','.join(['%s="%s"' % (name, value) for name, value in self.items()])

    def copy(self):
        """ Returns a copy of the labels """
        return Labels(super().copy(), logger=self.logger.parent, _log_init=False)
