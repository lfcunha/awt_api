from abc import ABCMeta


class BaseController(object):
    __metaclass__ = ABCMeta

    def __init__(self, controller_factory, req_handler, db):  # pragma: no cover
        self._controllers = controller_factory
        self._db = db
        self._req_handler = req_handler


    @property
    def controllers(self):  # pragma: no cover
        return self._controllers

    @property
    def req_handler(self):  # pragma: no cover
        return self._req_handler

    @property
    def logger(self):  # pragma: no cover
        """
        :rtype: athena.util.logger.logger._Logger | None
        """
        return self.request_handler_properties.request.api.logger


    @property
    def db(self):  # pragma: no cover
        """
        essentially an alias to the sqlalchemy session created in hermes.py
        :return: the active sqlalchemy (thread-safe) postgres session active for the API.
        :rtype: sqlalchemy.orm.session.Session
        """
        print(self._db.pool.qsize())
        if self._db.pool.qsize() < 2:
            self._db._re_initialize_pool()
        return self._db


class ModelControllerFactory(object):
    """
    a factory which creates/provides controllers on demand to resources.
    NOTE: this factory is intended to be instantiated anew on every request. while this seems like an unnecessary
          overhead to impose on *every* request, this factory is built in such a way that a given controller is only
          instantiated when needed by the resource referencing it. thus, while a factory is created, controllers are
          not created until needed.
    """

    # TODO: rename resource handler properties to request handler properties throughout
    def __init__(self, req_handler, config, logger):
        """
        :type request_handler_properties: hermes.tools.falcon_.request_handler_properties.RequestHandlerProperties
        :type postgres_sqlalchemy_session: sqlalchemy.orm.session.Session
        :type redis: redis.Redis
        """
        self._req_handler = req_handler
        self._config = config
        self._logger = logger
        self.controllers = {}

    def _get_controller(self, controller_class):
        """
        :param BaseModelController controller_class: the controller to return or instantiate if it has not already been.
        """
        if controller_class.__name__ not in self.controllers:
            self.controllers[controller_class.__name__] = controller_class(self, self._config, self._logger)  #initialize with db, etc
        return self.controllers[controller_class.__name__]

    # TODO: add controller properties here as required

    @property
    def fse(self):
        """
        :rtype: hermes.controllers.agencies import Agency
        """
        from swt.controllers.fse import FSE
        return self._get_controller(FSE)

    @property
    def extracts(self):
        """
        :rtype: hermes.controllers.agencies import Agency
        """
        from swt.controllers.extracts import Extracts
        return self._get_controller(Extracts)

    @property
    def user(self):
        """
        :rtype: hermes.controllers.agencies import Agency
        """
        from swt.controllers.user import User
        return self._get_controller(User)

    @property
    def auth(self):
        """
        :rtype: hermes.controllers.agencies import Agency
        """
        from swt.controllers.auth import Auth
        return self._get_controller(Auth)

    @property
    def digs(self):
        """
        :rtype: hermes.controllers.agencies import Agency
        """
        from swt.controllers.digs import Digs
        return self._get_controller(Digs)

    @property
    def dpcc_sample(self):
        """
        :rtype: hermes.controllers.agencies import Agency
        """
        from swt.controllers.dpcc_sample import DpccSample
        return self._get_controller(DpccSample)

    @property
    def new_controller(self):
        """
        :rtype: TODO
        """
        raise NotImplementedError("A model controller has not been created for compliance_document.")


if __name__ == "__main__":  # pragma: no cover

    controllers = ModelControllerFactory("db goes here")
