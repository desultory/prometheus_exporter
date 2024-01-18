#!/usr/bin/env python3


from zenlib.util import init_logger, init_argparser, process_args

from .exporter import Exporter


def main():
    argparser = init_argparser(prog=__package__, description='Metric Exporter for Prometheus')
    logger = init_logger(__package__)

    argparser.add_argument('-p', '--port', type=int, nargs='?', help='Port to listen on.')
    argparser.add_argument('-a', '--address', type=str, nargs='?', help='Address to listen on.')

    args = process_args(argparser, logger=logger)

    kwargs = {'logger': logger}

    if args.port:
        kwargs['listen_port'] = args.port
    if args.address:
        kwargs['listen_ip'] = args.address

    exporter = Exporter(**kwargs)
    exporter.start()


if __name__ == '__main__':
    main()
