from .exporter import Exporter
from .cached_exporter import cached_exporter
from .metric import Metric
from .labels import Labels

DEFAULT_EXPORTER_ARGS = [
    {'flags': ['-p', '--port'], 'dest': 'listen_port', 'type': int, 'nargs': '?', 'help': 'Port to listen on.'},
    {'flags': ['-a', '--address'], 'dest': 'listen_ip', 'type': str, 'nargs': '?', 'help': 'Address to listen on.'},
    {'flags': ['config_file'], 'type': str, 'nargs': '?', 'help': 'Config file to use.'}]

__all__ = ['Exporter', 'cached_exporter', 'Metric', 'Labels', 'DEFAULT_EXPORTER_ARGS']
