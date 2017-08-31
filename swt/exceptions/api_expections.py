import os
import configparser
import boto
from flask import g


"""
class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv
"""


class ApiException(Exception):
    """
    Generic class to handle APIExceptions
    Note: We should not be throwing this Exception unless there is an no relevant subclass present
    this by default sets the status code to 500
    we support the message code to support legacy APIException class which reads from the ini file to set the
    error description.
    """
    def __init__(self, title=None, description=None, code=500, exception_code=None, language='us_en',
                 **kwargs):
        """
        :param title: optional string. default to "Internal Server Error".
        :param description: optional string . default: "There was an error in your request". This can also
               be overridden by passing a message code which looks for the description in the exceptions.ini file
        :param code: http_status_code.
        :param exception_code: code if present in the exceptions.ini file
        :param kwargs: any additional params to be sent in the body of the response
        :return: None
        """
        self.title = title if title else 'Internal Server Error'
        self.description = self.get_exception_message(exception_code, language) if exception_code \
            else description if description else 'Looks like something went wrong. Please try again later.'

        self.additional_params = kwargs
        self.code = code
        self.exception_code = exception_code
        self._logger = self.additional_params["logger"] if "logger" in self.additional_params else None
        self._config = self.additional_params["config"] if "config" in self.additional_params else None

        if self._logger:
            """during tests, log level is set to critical (50), so errors won't be logged
            """
            try:
                username = g.username
            except Exception:  # if error in authentication, user will not be set
                username = None
            self._logger.error("user: {} - status_code: {} - exception_code: {} - Title: {} - Description: {}".
                               format(username, self.code, self.exception_code, self.title, self.description))
            if "stacktrace" in self.additional_params:
                self._logger.error("stacktrace: {}".format(self.additional_params.get("stacktrace")))

        if self._config and self._logger.getEffectiveLevel() < 50 and self._config.get("api", "env") == "prod":
            """Only send out emails in production, and if not running tests
            when running tests, log level is set to 50 (critica)
            """

            # we need the controller to access the config
            # We could set the test/testing property in the config, but then have to use a controller to set it on every request
            # unless perhaps create_app also returned the controller, so it could be set once in the fixture
            # #request.controllers._config.set("tests", "testing", "True")
            # if testing != "True":
            # instead, I'm relying on the loglevel being set to critical during tests

            aws_configuration = {
                'aws_access_key_id': self._config.get('aws', 'aws_access_key_id'),
                'aws_secret_access_key': self._config.get('aws', 'aws_secret_access_key'),
                'region_name': self._config.get('aws', 'aws_region')
            }

            conn = boto.ses.connect_to_region(**aws_configuration)
            email_from = 'support@niaidceirs.org'
            email_subject = 'SWT PYTHON API ERROR'
            email_body = """
                        <p>User: {} </p>
                        <p>Status Code: {} </p>
                        <p>Exception code: {}</p>
                        <p>Title: {}</p>
                        <p>Description: {}
                        <p>Stacktrace: {}</p>""".format(username, self.code, self.exception_code, self.title, self.description, self.additional_params.get("stacktrace", ""))

            email_to = self._config.get('admin', 'email')
            conn.send_email(email_from, email_subject, None, to_addresses=email_to, format="html",
                                      html_body=email_body)

    @staticmethod
    def handle(ex, req, resp, params):
        resp.status = ex.code
        resp.body = {
            'title': ex.title,
            'description': ex.description,
            'message': ex.title,
            'additional_info': ex.additional_params,
            "status": False,
            "statusText": ex.description
        }

    @staticmethod
    def get_exception_message(exception_key, language):
        """
        Extracts the exception message for a given exception key from the config exceptions file
        :param exception_key: key to find in config exceptions file
        :param language: string
        :rtype exception_description: string
        """
        config = configparser.ConfigParser()
        exceptions_list_path = os.path.dirname(os.path.realpath(__file__)) + '/api_exceptions_' + language + '.ini'
        config.read_file(open(exceptions_list_path))

        return config.get("EXCEPTIONS", exception_key)


class ApiInvalidPayloadException(ApiException):
    """
    JSON schema validator exception. This exception adds json schema message and path to the exception
    """
    def __init__(self, title=None, description=None, code=412, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Invalid Payload'
        description = description if description else 'Request payload is invalid.'

        super(ApiInvalidPayloadException, self).__init__(title=title, description=description, code=code,
                                                         exception_code=exception_code, **kwargs)



class ApiJsonSchemaValidationException(ApiException):
    """
    JSON schema validator exception. This exception adds json schema message and path to the exception
    """
    def __init__(self, title=None, description=None, code=422, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Json Schema Error'
        description = description if description else 'The payload verification failed.'

        if 'json_schema_path' in kwargs:
            kwargs['json_schema_path'] = '-'.join(str(item) for item in kwargs['json_schema_path'])

        super(ApiJsonSchemaValidationException, self).__init__(title=title, description=description, code=code,
                                                               exception_code=exception_code, **kwargs)


class ApiNoResultSet(ApiException):
    """
    an "exception" (though not really. read below) to be thrown when attempting to build a result set that results in
     an empty response.

    NOTE: this does NOT return a status code indicating a problem. It returns a 204. This should be used when a result
          set can be optionally empty and not indicate problems for the requester (i.e., requesting a list of resources
          that may or may not actually exist.)
    """
    def __init__(self, title=None, description=None, code=412, exception_code=None, **kwargs):
        """
        title and description do not have default values as responses without content do not always require an
         explanation.
        """
        super(ApiNoResultSet, self).__init__(title=title, description=description, code=code,
                                             exception_code=exception_code, **kwargs)


class ApiPreconditionFailedException(ApiException):
    """
    precondition failed exception
    """
    def __init__(self, title=None, description=None, code=412, exception_code=None, **kwargs):
        """
        :rtype: None
        """

        title = title if title else 'Precondition failed'
        description = description if description else 'a pre-condition for the request payload failed.'
        super(ApiPreconditionFailedException, self).__init__(title=title, description=description, code=code,
                                                             exception_code=exception_code, **kwargs)


class ApiPresentationException(ApiException):
    """
    This exception should be raised when an error during presentation modifications occurs.
    """

    def __init__(self, title=None, description=None, code=500, exception_code=None, **kwargs):
        title = title if title else 'Presentation failure'
        description = description if description else 'An error occurred when attempting to modify the presentation ' \
                                                      'of the requested resource.'

        super(ApiPresentationException, self).__init__(title=title, description=description, code=code,
                                                       exception_code=exception_code, **kwargs)


class ApiResourceAlreadyExists(ApiException):
    """
    This exception should be raised when a request to create a resource that already exists is made.

    NOTE: this is only necessary to raise when there is a need to preserve unique aspects of resources AND inform
          the user that a resource already exists.
    """
    def __init__(self, title=None, description=None, code=409, exception_code=None, **kwargs):
        title = title if title else 'Resources already exists'
        description = description if description else 'The resource attempting to be created already exists.'

        super(ApiResourceAlreadyExists, self).__init__(title=title, description=description, code=code,
                                                       exception_code=exception_code, **kwargs)


class ApiResourceNotFoundException(ApiException):
    """ Resource not found exception. """
    def __init__(self, title=None, description=None, code=404, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Resource Not Found Error'
        description = description if description else 'The requested resource could not be found.'

        super(ApiResourceNotFoundException, self).__init__(title=title, description=description, code=code,
                                                           exception_code=exception_code, **kwargs)


class ApiRethinkException(ApiException):
    """
    rethink db exception, will throw a 500 status unless overridden
    """
    def __init__(self, title=None, description=None, code=500, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Rethink Error'
        description = description if description else 'There was a rethink db operation error.'

        super(ApiRethinkException, self).__init__(title=title, description=description, code=code,
                                                  exception_code=exception_code, **kwargs)


class ApiSqlException(ApiException):
    """
    Generic SqlAlchemyException. Will throw a 500 status unless overridden
    """
    def __init__(self, title=None, description=None, code=412, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'MySQL Error'
        description = description if description else 'A postgres operation failed.'

        super(ApiSqlException, self).__init__(title=title, description=description, code=code,
                                              exception_code=exception_code, **kwargs)


class ApiSqlIntegrityException(ApiSqlException):
    """
    sqlalchemy integrity exception, will throw a 400 status unless overridden
    """
    def __init__(self, title=None, description=None, code=400, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Postgres Integrity Error'
        description = description if description else 'There was a postgres integrity error.'

        super(ApiSqlException, self).__init__(title=title, description=description, code=code,
                                              exception_code=exception_code, **kwargs)


class ApiUserNotAuthenticatedException(ApiException):
    """
    This exception should be raised when any type of request does not contain a valid token value. Will only be used
    by the auth middleware
    """

    def __init__(self, title=None, description=None, code=403, exception_code=None, **kwargs):
        title = title if title else 'Access denied.'
        description = description if description else 'Please provide a valid authentication token.'
        super(ApiUserNotAuthenticatedException, self).__init__(title=title, description=description, code=code,
                                                               exception_code=exception_code, **kwargs)


class ApiUserNotAuthorizedException(ApiException):
    class ApiNoResultSet(ApiException):
        """
        This exception should be raised when any type of request is made against a resource that the requester is not
         authorized to view and/or change.
        """

    def __init__(self, title=None, description=None, code=403, exception_code=None, **kwargs):
        title = title if title else 'Access denied.'
        description = description if description else 'You are not authorized to view the requested resource.'
        super(ApiUserNotAuthorizedException, self).__init__(title=title, description=description, code=code,
                                                            exception_code=exception_code, **kwargs)

class ApiUnauthorizedOperationException(ApiException):
    """
    Generic SqlAlchemyException. Will throw a 500 status unless overridden
    """
    def __init__(self, title=None, description=None, code=500, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Api Error'
        description = description if description else 'Operation not authorized.'

        super(ApiUnauthorizedOperationException, self).__init__(title=title, description=description, code=code,
                                              exception_code=exception_code, **kwargs)