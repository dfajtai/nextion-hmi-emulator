import pytest

from helpers import SAMPLE
from nextion_parser import parser


@pytest.fixture(scope="module")
def project():
    """The sample project, parsed once per test module."""
    return parser.load(SAMPLE)
