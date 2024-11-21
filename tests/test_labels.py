from unittest import TestCase, main, expectedFailure
from prometheus_exporter import Labels
from zenlib.logging import loggify


@loggify
class TestLabels(TestCase):
    @expectedFailure
    def test_non_str(self):
        labels = Labels()
        labels['a'] = 1  # Should raise a ValueError

    @expectedFailure
    def test_non_str_key(self):
        labels = Labels()
        labels[1] = 'a'  # Should raise a ValueError

    def test_preallocated(self):
        test_labels = {'a': '1234', 'b': '5678'}
        labels = Labels(test_labels)
        self.assertEqual(labels, test_labels)

    @expectedFailure
    def test_empty_value(self):
        labels = Labels()
        labels['a'] = ''

    @expectedFailure
    def test_numeric_key(self):
        labels = Labels()
        labels['1a'] = 'a'

    def test_underscore_key(self):
        labels = Labels()
        labels['_a'] = 'a'

    @expectedFailure
    def test_bad_preallocated(self):
        test_labels = {'a': 1234, 1: '5678'}
        Labels(test_labels)  # Should raise a ValueError

    def test_copy(self):
        test_labels = {'a': '1234', 'b': '5678'}
        labels = Labels(test_labels)
        copy_labels = labels.copy()
        self.assertEqual(labels, copy_labels)
        other_copy = labels.copy()
        other_copy.pop('a')
        other_copy.pop('b')
        self.assertEqual(labels, copy_labels)  # Should not be affected by other_copy

    def test_copy_with_logger(self):
        test_labels = {'a': '1234', 'b': '5678'}
        labels = Labels(test_labels, logger=self.logger)
        copy_labels = labels.copy()
        self.assertEqual(labels, copy_labels)



if __name__ == '__main__':
    main()
