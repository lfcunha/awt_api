import sys, os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + "/..")
import unittest
import pytest
from swt.swt_app import create_app as create_app_
from flask.ext.testing import TestCase
from urllib.request import urlopen
from flask_testing import LiveServerTestCase
from flask import request
from flask import appcontext_pushed, g
from flask import Response
from swt.controllers.fse import FSE
from swt.exceptions.api_expections import ApiPreconditionFailedException
import json

class TestEndpoints(unittest.TestCase):

    @pytest.fixture
    def create_app(self):
        app = create_app_()
        app.config['TESTING'] = True
        app_ = app.test_client()
        return app_

    def create_app_with_authtoken(self):
        app = create_app_()
        app.config['TESTING'] = True
        app_ = app.test_client()
        res = app_.get("/authorizationtoken/lcunha")
        data = res.data
        auth_token = json.loads(data.decode("utf-8"))
        return app_, auth_token

    def test_endpoint_authorizationtoken(self):
        app_ = self.create_app()
        res = app_.get("/authorizationtoken/lcunha")
        data = res.data
        data = data.decode("utf-8")
        status_code = res.status_code
        assert status_code == 200
        assert len(data) > 50
        assert "." in data

    def test_endpoint_extracts(self):
        app_, token = self.create_app_with_authtoken()
        auth_header = """{} {}""".format("Bearer", token)
        try:
            resp = app_.get("/extracts", headers={'Authorization': auth_header})
        except Exception as e:
            print(e)
        else:
            assert resp.status_code == 200
            res = json.loads(resp.data.decode("utf-8"))
            assert res.get("status") == True
            assert "core" in res
            assert len(res.get("requesters", {})) > 0
            assert len(res.get("extracts", [])) > 0


    # def test_endpoint_fse(self):
    #     app_, token = self.create_app_with_authtoken()
    #     auth_header = """{} {}""".format("Bearer", token)
    #     resp = app_.post("/fse",
    #                     headers={'Authorization': auth_header},
    #                     data=json.dumps({"zipcode": 11215,
    #                                      "number_extracts": 1,
    #                                      "analysis_type": ["Phylogenetics"],
    #                                      "sequencing_tech": ["Illumina NextSeq"],
    #                                      }),
    #                     content_type='application/json')
    #     res = json.loads(resp.data.decode("utf-8"))
    #     self.assertEqual(int(resp.status_code), 200)
    #     self.assertIn("0", res)
    #     self.assertIn("1", res)
    #     self.assertIn("contact_email", res)
    #
    #     """Assert Zipcode Validation"""
    #     resp = app_.head("/fse/11215", headers={'Authorization': auth_header})
    #     self.assertEqual(int(resp.status_code), 204)
    #
    #     with pytest.raises(ApiPreconditionFailedException):
    #         app_.head("/fse/11215a", headers={'Authorization': auth_header})
    #
    #     assert True

    def test_existing_endpoint_user(self):
        app_, token = self.create_app_with_authtoken()
        auth_header = """{} {}""".format("Bearer", token)
        resp = app_.get("/users/lcunha", headers={'Authorization': auth_header})
        res = json.loads(resp.data.decode("utf-8"))
        print(res)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(res.get("ldap"), dict)
        self.assertIn("ldap", res)
        self.assertEqual(res.get("ldap"), {})
        self.assertIn("swt", res)
        self.assertIsInstance(res.get("swt"), dict)
        self.assertGreater(len(res.get("swt")), 0)
        self.assertIn("institution", res.get("swt"))

    def test_non_existing_endpoint_user(self):
        app_, token = self.create_app_with_authtoken()
        auth_header = """{} {}""".format("Bearer", token)
        resp = app_.get("/users/lcunha1", headers={'Authorization': auth_header})
        res = json.loads(resp.data.decode("utf-8"))
        self.assertEqual(int(resp.status_code), 200)
        self.assertIsNone(res.get("user"))
        self.assertEqual(res.get("ldap"), {})
        self.assertEqual(res.get("swt"), {})
