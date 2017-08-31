from ._controller import ModelControllerFactory as _controller
from swt.schema.models.user import UserLdap, UserSwt, User
from swt.exceptions.api_expections import ApiPreconditionFailedException
import jwt
import time
import traceback

class Auth(_controller):
    def __init__(self, *args):
        super(Auth, self).__init__(*args)

    def get_token(self, user):

        user_ldap = user.get("ldap", {})

        if not user_ldap:
            raise ApiPreconditionFailedException(description="cannot get user information from ldap")

        username = user_ldap.get("actor_username")

        first_last_name = "{} {}".format(user_ldap.get("actor_first_name", username),
                                         user_ldap.get("actor_last_name", username))
        #roles = user.get("ldap", {}).get("groups")
        user_groups = user_ldap.get("groups", {}) if user_ldap.get("groups") else {}
        try:
             digs = list(map(lambda x: x.split("-CoreAdmin")[0], filter(lambda x: "coreadmin" in x.lower(), user_groups.keys())))
        except Exception as e:
            """actor api group is a empty list when there's no values (otherwise it's an object of objects)
            """
            #self._logger.error(e, exc_info=True)
            tb = traceback.format_exc()
            raise ApiPreconditionFailedException(description="Error getting CoreAdmin", title="Error getting CoreAdmin",
                                                 stacktrace=tb,
                                                 logger=self._logger, config=self._config)
            #digs = []

        if user:
            payload = dict()
            payload["Audience"] = self._config.get("api", "origin")
            payload["Id"] = "57420e258cc15"
            payload["IssuedAt"] = time.time()
            payload["IssuedAt"] = time.time()
            payload["Expiration"] = time.time() + 43200
            payload["username"] = username
            payload["first_last_name"] = first_last_name
            #payload["roles"] = roles
            payload["digs"] = digs

            encoded = jwt.encode(payload, self._config.get("jwt", "secret"), algorithm='HS256')

            return encoded.decode("utf-8")

            #decoded = jwt.decode(encoded, self._config.get("jwt", "secret"), algorithms=['HS256'])
