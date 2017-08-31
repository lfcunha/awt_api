import sys, os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + "/..")
import unittest
import pytest
from swt.swt_app import create_app as create_app_
from swt.controllers.fse import FSE


class TestFse(unittest.TestCase):

    @pytest.fixture
    def create_app(self):
        app = create_app_(testing=True)
        app.config['TESTING'] = True
        return app

    def test_stuff(self):
        assert True
