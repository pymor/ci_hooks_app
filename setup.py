""" Setup script for the ci-hooks-app application.

"""

from os import walk
from os.path import join
from setuptools import find_packages
from setuptools import setup


def _listdir(root):
    """ Recursively list all files under 'root'.

    """
    for path, _, names in walk(root):
        yield path, tuple(join(path, name) for name in names)
    return


_CONFIG = {
    "name": "ci_hooks_app",
    "author": "René Fritze",
    "author_email": "rene.fritze@wwu.de",
    "url": "",
    "package_dir": {"": "src"},
    "packages": find_packages("src"),
    "entry_points": {
        "console_scripts": ("ci_hooks_app = ci_hooks_app.cli:main",),
    },
}


def _version():
    """ Get the local package version.

    """
    path = join("src", _CONFIG["name"], "__version__.py")
    namespace = {}
    with open(path) as stream:
        exec(stream.read(), namespace)
    return namespace["__version__"]


def main():
    """ Execute the setup commands.

    """
    _CONFIG["version"] = _version()
    setup(**_CONFIG)
    return 0


# Make the script executable.

if __name__ == "__main__":
    raise SystemExit(main())
