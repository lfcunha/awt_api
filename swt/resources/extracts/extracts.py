from flask_restful import Resource, request
import json
from swt.exceptions.api_expections import ApiPreconditionFailedException


class Extracts(Resource):

    def get(self):
        extracts = self.controllers.extracts.get_extracts(request.user)
        return extracts, 200

    def post(self):
        payload = request.get_json(force=True)
        insertion = self.controllers.extracts.insert_extracts(request.user, payload)
        return insertion, 201

    def put(self):
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception as e:
            raise ApiPreconditionFailedException(title="Application Error.", description="Application Error.")
        self.controllers.extracts.update_status(request.user, payload=payload)
        return None, 204
