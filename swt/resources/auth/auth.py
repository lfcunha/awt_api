from flask_restful import Resource


class AuthorizationToken(Resource):

    def get(self, username):
        user = self.controllers.user.get_user(username)
        return self.controllers.auth.get_token(user), 200
