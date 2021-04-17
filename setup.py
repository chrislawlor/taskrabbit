from setuptools import setup
import os
import sys
from pathlib import Path


assert sys.version_info >= (3, 6, 0), "taskrabbit requires Python 3.6+"

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

EXTENSIONS = ["postgres"]


def get_long_description() -> str:
    return (PROJECT_DIR / "README.md").read_text(encoding="utf8")


# REQUIREMENTS
# requirements parsing borrowed from Celery project.


def _strip_comments(line):
    return line.split("#", 1)[0].strip()


def _pip_requirement(req):
    if req.startswith("-r "):
        _, path = req.split()
        return reqs(*path.split("/"))
    return [req]


def _reqs(*f):
    return [
        _pip_requirement(r)
        for r in (
            _strip_comments(line)
            for line in open(os.path.join(os.getcwd(), "requirements", *f)).readlines()
        )
        if r
    ]


def reqs(*f):
    """Parse requirement file.
    Example:
        reqs('default.txt')          # requirements/default.txt
        reqs('extras', 'redis.txt')  # requirements/extras/redis.txt
    Returns:
        List[str]: list of requirements specified in the file.
    """
    return [req for subreq in _reqs(*f) for req in subreq]


def extras(*p):
    """Parse requirement in the requirements/extras/ directory."""
    return reqs("extras", *p)


def install_requires():
    """Get list of requirements required for installation."""
    return reqs("base.txt")


def extras_require():
    """Get map of all extra requirements."""
    return {x: extras(x + ".txt") for x in EXTENSIONS}


setup(
    name="taskrabbit",
    version="0.3.0",
    description="Move Celery tasks in and out of RabbitMQ",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Chris Lawlor",
    url="https://github.com/chrislawlor/taskrabbit",
    license="MIT",
    packages=["taskrabbit", "taskrabbit.stores"],
    python_requires=">=3.6",
    zip_safe=False,
    install_requires=install_requires(),
    extras_require=extras_require(),
    entry_points={
        "console_scripts": [
            "taskr = taskrabbit.__main__:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Distributed Computing",
        "Topic :: Software Development :: Object Brokering",
        "Operating System :: OS Independent",
    ],
)
