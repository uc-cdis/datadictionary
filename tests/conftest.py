"""
    Conftest.py a configuration file for pytest
"""
import os

import pytest
from gdcdictionary import SCHEMA_DIR, GDCDictionary
from tests.utils import load_yaml


@pytest.fixture(scope="session")
def dictionary():
    return GDCDictionary(root_dir=SCHEMA_DIR)


@pytest.fixture(scope="session")
def definitions(dictionary):
    return load_yaml(os.path.join(SCHEMA_DIR, '_definitions.yaml'))


@pytest.fixture(scope="session")
def schema(dictionary):
    return dictionary.schema
