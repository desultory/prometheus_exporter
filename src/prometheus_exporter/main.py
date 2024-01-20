from zenlib.util import get_kwargs
from .exporter import Exporter
from .__init__ import DEFAULT_EXPORTER_ARGS


def main():
    kwargs = get_kwargs(package=__package__, description='Metric Exporter for Prometheus',
                        arguments=DEFAULT_EXPORTER_ARGS)

    exporter = Exporter(**kwargs)
    exporter.start()


if __name__ == '__main__':
    main()
