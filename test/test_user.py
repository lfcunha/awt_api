import sys, os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + "/..")
import unittest
from unittest import mock
import pytest

from swt.swt_app import create_app as create_app_, prepare_response
from flask import request
from swt.exceptions.api_expections import ApiPreconditionFailedException
from .config import *
from .data.mocked_requests import mocked_requests_get


class TestUser(unittest.TestCase):

    @pytest.fixture
    def create_app(self):
        app = create_app_(testing=True)  #turn off logging/emailing for tests
        app.config['TESTING'] = False
        return app

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_user_controller(self, mock_get):
        app = self.create_app()
        with app.test_client() as c:
            res = c.get("/test/")
            status_code = res.status_code
            self.assertEqual(status_code, 200)
            app.preprocess_request()
            user = request.controllers.user.get_user(test_username)
            self.assertIsInstance(user, dict)
            self.assertEqual(all(["ldap" in user, "swt" in user]), True)
            self.assertEqual(user.get("swt", {}).get("username"), test_username)
            self.assertEqual(user.get("ldap", {}).get("actor_username"), test_username)
            with pytest.raises(ApiPreconditionFailedException):
                request.controllers.user.get_user(non_existent_user)
            with pytest.raises(ApiPreconditionFailedException):
                request.controllers.user.get_user(None)
            user_put["user_has_been_updated"] = False
            assert not request.controllers.user.upsert_user(test_username, user_put)
            user_put["user_has_been_updated"] = True
            assert request.controllers.user.upsert_user(test_username, user_put)
            user_put["username"] = test_username + "_temp"
            user_put["email"] = test_username + "_temp@gmail.com"
            assert request.controllers.user.upsert_user(user_put["username"], user_put)
            assert request.controllers.user.delete_user(user_put["username"])
            user_put["username"] = test_username
            user_put["email"] = test_username + "@gmail.com"
        assert True