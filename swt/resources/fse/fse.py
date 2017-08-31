from flask import request
from flask_restful import Resource
from swt.exceptions.api_expections import ApiException


class Facilities(Resource):
    def post(self):
        try:
            data = request.get_json(force=True)
            zipcode = data.get('zipcode', None)
        except Exception as e:  # pragma: no cover
            raise ApiException(description=e,
                               title="failed to read data",
                               config=self.controllers._config,
                               logger=self.controllers._logger)
        number_extracts = int(data.get("number_extracts", None))
        sequencing_tech = data.get("sequencing_tech", None)
        post_seq_analysis = data.get("analysis_type", None)
        country = data.get("country", None)
        facilities = self.controllers.fse.select_facility(zipcode, country, number_extracts, sequencing_tech, post_seq_analysis)
        return facilities, 200


class FacilitiesValidate(Resource):
    def head(self, zipcode):
        """Validate the zipcode.
        Call to validate_zipcode will throw a precondition failed exception if it fails

        Args:
            zipcode:

        Returns:
        """
        self.controllers.fse.validate_zipcode(zipcode)
        return None, 204
