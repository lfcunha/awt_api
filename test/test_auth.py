import sys
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + "/..")
import unittest
from unittest import mock
import pytest
from swt.swt_app import create_app as create_app_, prepare_response
from flask import request
from swt.exceptions.api_expections import ApiPreconditionFailedException
import json
from .config import *
import jwt
from .data.mocked_requests import *


class TestAuth(unittest.TestCase):

    @pytest.fixture
    def create_app(self):
        app = create_app_(testing=True)  #turn off logging/emailing for tests
        app.config['TESTING'] = False
        return app

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_auth_controller(self, mock_get):
        app = self.create_app()
        with app.test_client() as c:
            res = c.get("/test/")
            assert res.status_code == 200
            app.preprocess_request()

            # request.controllers._config.set("tests", "testing", "True")  # set testing to prevent sending out exception emails
            user = request.controllers.user.get_user(test_username)
            # request.controllers._logger.setLevel(50)
            token = request.controllers.auth.get_token(user)
            assert len(token) > 50
            assert "." in token
            decoded_token = jwt.decode(token, request.controllers.user._config.get("jwt", "secret"), algorithms=['HS256'])
            assert decoded_token.get("username") == test_username

            with pytest.raises(ApiPreconditionFailedException):
                """getting a non-existent user should rause exception"""
                request.controllers.user.get_user(non_existent_user)
            with pytest.raises(ApiPreconditionFailedException):
                """IF getting non-existent user did not raise exception,
                getting the token on such case should raise exception"""
                request.controllers.auth.get_token(
                    non_existent_user_ldap)  # This should not be called, since an exception is raised getting the user, but if it would, should raise Exception of its own

            # create groups = None should not raise exception
            non_existent_user_ldap["ldap"] = {'actor_username': '', 'actor_first_name': 'Luis',
                                              'groups': None}
            assert request.controllers.auth.get_token(non_existent_user_ldap)
        assert True

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def get_token(self, mock_get):
        app = self.create_app()
        with app.test_client() as c:
            res = c.get("/test/")
            status_code = res.status_code
            assert status_code == 200

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_auth(self, mock_get):
        """Test /authorizationtoken/lcunha with mock ldap call, and local mysql db
        Individual functions used in the endpoint tested separately

        :param mock_get:
        :return:
        """
        app = self.create_app()
        with app.test_client() as c:
            res = c.get("/authorizationtoken/lcunha")
            data = res.data
            data = data.decode("utf-8")
            status_code = res.status_code
            assert status_code == 200
            assert len(data) > 50
            assert "." in data

        assert True

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_authentication(self, mock_get):
        """Make a request with a invalid token. It should return a 401 (unauthorized)

        :param mock_get:
        :return:
        """
        app = self.create_app()
        with app.test_client() as app_:
            data = app_.get("/authorizationtoken/lcunha").data
            token = json.loads(data.decode("utf-8"))
            token = token.replace("r", "S").replace("8", "0").replace("a", "Z")  # corrupt the token
            auth_header = """{} {}""".format("Bearer", token)
            res = app_.get("/extracts/", headers={'Authorization': auth_header})
            status_code = res.status_code
            data = json.loads(res.data.decode('utf-8'))
            assert all([not data, int(status_code) == 401])

        assert True