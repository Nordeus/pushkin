from . import context
from . import config
from . import pushkin_cli
from os.path import dirname, join, abspath
test_config_ini_path = abspath( join(dirname(__file__), 'tests', 'test_config.ini') )
tests_directory_path = abspath( join(dirname(__file__), 'tests') )

def run_tests():
    import pytest
    pytest.main(tests_directory_path)
