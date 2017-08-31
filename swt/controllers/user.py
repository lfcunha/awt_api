from ._controller import ModelControllerFactory as _controller
from swt.schema.models.user import UserLdap, UserSwt, User
from flask import g
import requests
from swt.exceptions.api_expections import ApiPreconditionFailedException, ApiSqlException
import sys
import pymysql


def get_user_swt(username):
    conn = g._db

    with conn.cursor() as cursor:

        """
        Get List of DIGS facilities with the required technology
        """

        cursor.execute("SELECT * FROM Users WHERE `username` LIKE \"{}\"".format(username))

        columns = [field[0] for field in cursor.description]
        user = UserSwt()

        for row in cursor:
            for k, v in zip(columns, row):
                setattr(user, k, v)
        cursor.close()

    user_ = user.__dict__
    return user_ if user_ else {}


def get_user_ldap(username, config):
    if not username:
        return {}   # pragma: no cover
    ldap_url = config.get('ldap', 'url')

    r = requests.get(ldap_url + username, timeout=2)

    rj = r.json()
    if "status" in rj:
        if not rj["status"]:
            return {}

    return {k:v for k, v in rj.items()}
    """build user instance. Not in use, since there's no need for the complexity of a class and a dict will do as well"""
    #for k, v in rj.items():
    #    setattr(user, k, v)
    #return user.__dict__


class User(_controller):
    def __init__(self, *args):
        super(User, self).__init__(*args)

    def _get_user(self, username, swt, ldap):
        """

        :param username: string
        :param swt: Boolen
        :param ldap: Boolen
        :return: dict
        """
        if not username:
            raise ApiPreconditionFailedException(title="Missing username in call to get user", descriptio="Failed to get user information")
        user = {"ldap": {}, "swt": {}}
        if ldap:
            user["ldap"] = get_user_ldap(username, self._config)
            if not user["ldap"]:
                raise Exception("User does not exist")
        if swt:
            user["swt"] = get_user_swt(username) if swt else None  # no need to raise exception if fails because just used to pre-fill user info form, which the user can still do
            if user["swt"]:
                user["swt"]["created"] = None  # remove datime object, since json can't serialize it (could use  default=json_util.default param to json.dumps)
                user["swt"]["modified"] = None
        return user

    def get_user(self, username, swt=True, ldap=True):
        try:
            return self._get_user(username,  swt, ldap)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise ApiPreconditionFailedException(title=str(e), description=str(e),
                                                 logger=self._logger, config=self._config, stacktrace=exc_value)

    def delete_user(self, username):
        conn = g._db
        db_name = self._config.get("MySql", "db")
        success = False
        with conn.cursor() as cursor:
            try:
                success = cursor.execute("DELETE FROM `{}`.`Users` WHERE `username` LIKE \"{}\"".format(db_name, username))
                if success:
                    conn.commit()
            except Exception as e:  # pragma: no cover
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ApiSqlException(title="failed to delete user", description=str(e),
                                      logger=self._logger, config=self._config,
                                      stacktrace=exc_value)
        return success

    def upsert_user(self, username, data):
        if not bool(data.get("user_has_been_updated")):
            return False
        conn = g._db
        db_name = self._config.get("MySql", "db")
        success = False
        with conn.cursor() as cursor:
            try:
                cursor.execute("SELECT * FROM `{}`.`Users` WHERE `username` LIKE \"{}\"".format(db_name, username))
            except Exception as e:  # pragma: no cover
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ApiSqlException(title="failed to query user", description=str(e),
                                      logger=self._logger, config=self._config,
                                      stacktrace=exc_value)
            res = cursor.fetchall()
            if not res:
                query = """INSERT INTO `{}`.`Users` (`username`, `name`, `institution`, `street_address`, `city`, `state_province`, `zipcode`, `country`, `daytime_phone`, `email`, `created`, `modified` )
                  VALUES (\"{}\", \"{}\", \'{}\', "{}", \"{}\", \"{}\", \"{}\", \"{}\", \"{}\", \"{}\", NOW(), NOW())"""\
                    .format(db_name,
                            data.get("username", ""),
                            data.get("name", ""),
                            data.get("institution", ""),
                            data.get("street_address", ""),
                            data.get("city", ""),
                            data.get("state_province", ""),
                            data.get("zipcode", ""),
                            data.get("country", ""),
                            data.get("daytime_phone", ""),
                            data.get("email", ""))
                try:
                    success = cursor.execute(query)
                    if success:
                        conn.commit()
                except pymysql.err.IntegrityError as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    title = "duplicate email" if "Duplicate entry" in str(exc_value) else "Failed to insert user information"
                    raise ApiSqlException(title=title, description="Failed to insert user information",
                                          logger=self._logger, config=self._config,
                                          stacktrace=exc_value)
                except Exception as e:  # pragma: no cover
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    raise ApiSqlException(title="Failed to insert user information", description="Failed to insert user information",
                                          logger=self._logger, config=self._config,
                                          stacktrace=exc_value)
            else:
                query = """UPDATE `{}`.`Users` SET
                                  `name`=\"{}\",
                                  `institution`=\"{}\",
                                  `street_address`=\"{}\",
                                  `city`=\"{}\",
                                  `state_province`=\"{}\",
                                  `zipcode`=\"{}\",
                                  `country`=\"{}\",
                                  `daytime_phone`=\"{}\",
                                  `email`=\"{}\",
                                  `modified`=NOW()
                           WHERE `username`
                           LIKE \"{}\"""" \
                    .format(db_name,
                            data.get("name", ""),
                            data.get("institution", ""),
                            data.get("street_address", ""),
                            data.get("city", ""),
                            data.get("state_province", ""),
                            data.get("zipcode", ""),
                            data.get("country", ""),
                            data.get("daytime_phone", ""),
                            data.get("email", ""),
                            data.get("username", ""),
                            )
                try:
                    success = cursor.execute(query)
                    if success:
                        conn.commit()
                except Exception as e:  # pragma: no cover
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    raise ApiSqlException(title="Failed to update user information", description=str(e),
                                          logger=self._logger, config=self._config,
                                          stacktrace=exc_value)
        return bool(success)

