import sys, os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + "/..")
import unittest
from unittest import mock
import pytest

from swt.swt_app import create_app as create_app_, prepare_response
from flask import request
from flask import appcontext_pushed, g
from flask import Response
from swt.controllers.fse import FSE
from swt.exceptions.api_expections import ApiPreconditionFailedException
import json
from .data.mocked_requests import mocked_requests_get


class TestFse(unittest.TestCase):

    @pytest.fixture
    def create_app(self):
        app = create_app_(testing=True)  #turn off logging/emailing for tests
        app.config['TESTING'] = False
        return app

    def test_zipcode_validation(self):
        """Test function used to validate zipcode
        """
        assert FSE.validate_zipcode(11215, 10029)

        with pytest.raises(Exception):
            FSE.validate_zipcode()

        with pytest.raises(ApiPreconditionFailedException):
            """Raises exception if error in zipcode"""
            FSE.validate_zipcode(11215, "10029a")

    # @mock.patch('requests.get', side_effect=mocked_requests_get)
    # def test_fse(self, mock_get):
    #     app = self.create_app()
    #     app_ = app.test_client()
    #     data = app_.get("/authorizationtoken/lcunha").data
    #     token = json.loads(data.decode("utf-8"))
    #     auth_header = """{} {}""".format("Bearer", token)
    #
    #     #asset mock request call made
    #     self.assertIn(mock.call('https://www.niaidceirs-staging.net/dpcc/api/actors/lcunha', timeout=2), mock_get.call_args_list)
    #
    #     """ Using context of extracts just to a initialize a simple request without params, not necessary testing that endpoint"""
    #     with app.test_request_context('/extracts/', method='get', headers = {'Authorization': auth_header}) as c:
    #         assert not getattr(g, '_db', None)  # g not available yet. need to pre-process request
    #
    #         assert request.path == '/extracts/'
    #         assert request.method == 'GET'
    #
    #         """Pre-process the request, which loads database into globals"""
    #         app.preprocess_request()
    #
    #         assert getattr(g, '_db', None)  # g is only available after pre-processing the request (and within this request context)
    #         sequencing_tech = ['Illumina NextSeq']
    #         db_name = "DPCC_SWT_DEV"
    #         conn = g._db
    #         with conn.cursor() as cursor:
    #             possible_digs, possible_digs_capacity, response, all_ids, full_list = FSE.get_possible_digs(cursor, db_name, sequencing_tech, "Phylogenetics")
    #         conn.close()  # if we prepare response, it would close it there
    #         assert isinstance(possible_digs, list)
    #         assert isinstance(possible_digs_capacity, list)
    #         assert isinstance(response, dict)
    #         assert isinstance(all_ids, list)
    #         assert isinstance(full_list, list)
    #
    #         assert not any(response.values())
    #         assert all([isinstance(x, int) for x in all_ids])
    #         assert all(["DIGS-" in x for x in full_list])
    #         assert all(["id" in possible_digs[0], "capacity_total" in possible_digs[0], "instruments_operational" in possible_digs[0]])
    #         assert all(["digs_id" in possible_digs_capacity[0], "capacity_total" in possible_digs[0]])
    #
    #         resp_body = {"abcd": 1}
    #         raw_resp = Response(json.dumps(resp_body))
    #         resp= app.after_request(prepare_response)(raw_resp)  # SWT's middleware function
    #         #resp = app.process_response(raw_resp)  # Flask's function
    #         self.assertEqual(json.loads(resp.data.decode("utf-8")), resp_body, "middleware must prepare response with jsonified objects")
    #     #sys.stderr.write("world\n")
    #     assert True

    def test_fail(self):
        assert True
