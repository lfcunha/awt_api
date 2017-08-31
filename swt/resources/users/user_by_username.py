from flask_restful import Resource, request
from swt.exceptions.api_expections import ApiPreconditionFailedException
import json


class UserUsername(Resource):
    def post(self):  # pragma: no cover
        pass

    def get(self, username):
        user = self.controllers.user.get_user(username, ldap=False)
        return user

    def put(self, username):
        try:
            data = request.get_data()
            data = json.loads(data.decode("utf-8"))
        except Exception as e:
            self._logger.error("can't read put data", exc_info=True)
            raise ApiPreconditionFailedException(description="Application Error.")
        else:
            res = self.controllers.user.upsert_user(username, data)
        return res

    def patch(self):  # pragma: no cover
        pass

    def patch(self):
        pass

    def options(self, username):
        return {'Allow': 'GET'}, 200, \
               {'Access-Control-Allow-Origin': '*', \
                'Access-Control-Allow-Methods': 'PUT,GET'}
