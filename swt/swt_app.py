from .middleware.middleware import prepare_response, prepare_request
from .controllers._controller import ModelControllerFactory

import configparser
from flask import Flask
from flask_restful import Api
import logging.handlers
from logging.config import dictConfig
import os
import datetime

from gevent import monkey
monkey.patch_socket()

from functools import partial
from swt.routes import routes
from logger_config import LOG_CONFIG


try:
    os.makedirs('/var/log/swt/api')  # docker should create this fir
except:
    pass #dir exists

# TODO: put logs in a separate EBS. https://docs.docker.com/engine/extend/EBS_volume/ or https://github.com/rancher/convoy
#LOG_FILENAME = '/var/log/swt/fse/' + __name__ + "_" + str(time.time()) + '.log'
#import random
LOG_FILENAME = '/var/log/swt/api/' + __name__ + "_" + str(datetime.date.today()) +'.log' #+ "_" + str(random.random()*100)+'.log'

_log_config = LOG_CONFIG
_log_config["handlers"]["file"]["filename"] = LOG_FILENAME
_log_config['loggers']["swt-api"]["level"] = "INFO"
dictConfig(_log_config)
_logger = logging.getLogger('swt-api')
LOGGER = _logger

config = configparser.ConfigParser()
config_path = os.path.dirname(os.path.realpath(__file__)) + '/config.ini'
config.read_file(open(config_path))
HOST = config.get('MySql', 'host')
PORT = int(config.get('MySql', 'port'))
DB = config.get('MySql', 'db')
USER = config.get('MySql', 'user') #os.getenv("RDS_SWT_USERNAME", "sl_dev_app")
PASSWD = config.get('MySql', 'passwd') #os.getenv("RDS_SWT_PASSWD", "sl_dev_@pp20878!")

# custom error messages to be included on the body of error response
errors = {
    'UserAlreadyExistsError': {
        'message': "A user with that username already exists.",
        'status': 409,
    },
    'ResourceDoesNotExist': {
        'message': "A resource with that ID no longer exists.",
        'status': 410,
        'extra': "Any extra information you want.",
    },
    "ApiException":   {
        'message': "A Application error happened.",
        'status': 500,
        'extra': "Any extra information you want.",
    },
}


def create_app(testing=False):
    app = Flask(__name__)
    api = Api(app, errors=errors)
    if testing:  # do not log errors for tests.
        _logger.setLevel(50)

    for uri, resource in routes.items():
        resource.logger = _logger
        resource.controllers = ModelControllerFactory(resource, config, _logger)
        resource.config = config
        api.add_resource(resource, uri)

    # add controller to the request so it can be used on tests
    pre_process = partial(prepare_request, config, ModelControllerFactory(None, config, _logger))

    # Middleware hooks
    app.before_request(pre_process)
    app.after_request(prepare_response)

    return app
