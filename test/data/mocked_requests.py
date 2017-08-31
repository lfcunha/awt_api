from .mocked_responses import *


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    url = args[0]

    if url == "https://www.niaidceirs-staging.net/dpcc/api/actors/lcunha":
        return MockResponse(user_ldap, 200)
    elif url == "https://www.niaidceirs-staging.net/dpcc/api/actors/lcunhaa":
        return MockResponse(non_existent_user_ldap, 200)
    else:
        return MockResponse({"key": "value"}, 200)

    return MockResponse({}, 404)
