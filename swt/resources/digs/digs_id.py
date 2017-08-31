from flask_restful import Resource, request
import json
#from werkzeug.urls import url_decode


class DigsId(Resource):

    def get(self, digs_facility_name):
        digs = self.controllers.digs.get_digs_by_id(request.user, digs_facility_name=digs_facility_name)
        return digs, 200

    def put(self, digs_facility_name):
        """
        not in use. Extracts endpoint takes id in the body
        :param id:
        :return:
        """
        payload = json.loads(request.data.decode("utf-8"))
        digs = self.controllers.digs.update_digs(request.user, digs_facility_name=digs_facility_name, update_params=payload)
        return digs, 204
