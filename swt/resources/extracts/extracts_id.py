from flask_restful import Resource, request


class ExtractsId(Resource):  # pragma: no cover

    def get(self, id):
        #extracts = self.controllers.extracts.get_extracts(request.user, id=id)
        #return extracts, 200
        pass

    def patch(self, id):
        """
        not in use. Extracts endpoint takes id in the body
        :param id:
        :return:
        """
        #payload = request.data.decode("utf-8")
        #extracts = self.controllers.extracts.update_status(request.user, id=id, payload=payload)
        #return extracts, 200
        pass
