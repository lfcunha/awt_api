from .resources.fse import Facilities, FacilitiesValidate
from .resources.digs import DigsId
from .resources.dpcc_sample import DpccSample
from .resources.extracts import Extracts, ExtractsId
from .resources.users.user_by_username import UserUsername
from .resources.auth.auth import AuthorizationToken
from .resources.test.test import TestResource


routes = {
    "/fse": Facilities,
    "/fse/<zipcode>": FacilitiesValidate,
    "/digs/<digs_facility_name>": DigsId,
    "/dpccsample/<sample_id>": DpccSample,
    "/extracts": Extracts,
    "/extracts/<id>": ExtractsId,
    "/users/<username>": UserUsername,
    "/authorizationtoken/<username>": AuthorizationToken,
    "/test/": TestResource

}