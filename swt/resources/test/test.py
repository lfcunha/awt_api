from flask_restful import Resource, request
from werkzeug.urls import url_decode
from swt.exceptions.api_expections import ApiPreconditionFailedException

class TestResource(Resource):  # pragma no cover
    def post(self):
        return {"test": 1}, 200

    def get(self):
        return {"status": True, "test": 1}, 200

    def put(self):
        return {"test": 1}, 200

    def patch(self):
        return {}, 200