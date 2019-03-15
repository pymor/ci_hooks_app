""" Implementation of the command line interface.

"""
import pprint
from argparse import ArgumentParser

from sanic.log import logger

from ci_hooks_app import __version__
from ci_hooks_app.config import config


def main(argv=None):
    """ Execute the application CLI.

    :param argv: argument list to parse (sys.argv by default)
    """
    args = _args(argv)
    logger.debug(args.warn)
    logger.debug("starting execution")

    config.read_file(open(args.config, 'rt'))
    # do not move, needs to be imported after config is set up
    from ci_hooks_app import server
    server.app.run(host="0.0.0.0", port=8080, debug=True)
    logger.debug("successful completion")

    return 0
 

def _args(argv):
    """ Parse command line arguments.

    :param argv: argument list to parse
    """
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", action="store",
            help="config file [etc/config.ini]")
    parser.add_argument("-v", "--version", action="version",
            version="ci-hooks-app {:s}".format(__version__),
            help="print version and exit")
    parser.add_argument("-w", "--warn", default="WARN",
            help="logger warning level [WARN]")

    args = parser.parse_args(argv)
    if not args.config:
        # Don't specify this as an argument default or else it will always be
        # included in the list.
        args.config = "config.ini"
    return args


def interactive(argv=None):
    """ Execute the application CLI.

    :param argv: argument list to parse (sys.argv by default)
    """
    args = _args(argv)
    logger.debug(args.warn)
    logger.debug("starting execution")

    config.read_file(open(args.config, 'rt'))
    # do not move, needs to be imported after config is set up
    from ci_hooks_app import server
    return server.github_app


if __name__ == "__main__":
    try:
        status = main()
    except:
        logger.critical("shutting down due to fatal error")
        raise  # print stack trace
    else:
        raise SystemExit(status)
