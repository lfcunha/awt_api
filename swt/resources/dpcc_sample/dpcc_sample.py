from flask_restful import Resource, request


class DpccSample(Resource):

    def get(self, sample_id):
        samples = self.controllers.dpcc_sample.get_dpcc_samples(request.user, sample_id=sample_id)
        return samples, 200
