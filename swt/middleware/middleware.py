from flask import request, make_response
import json
from flask import g
from swt.controllers.user import get_user_ldap, get_user_swt
import jwt
import re
import pymysql as db
from swt.exceptions.api_expections import ApiSqlException, ApiPreconditionFailedException


# these paths do not receive a jwt token
AUTHORIZED_PATHS = ["/authorizationtoken", "/test", "/favicon.ico"]


def authenticate(token, secret):
    try:
        jwt.decode(token, secret, algorithms=['HS256'])
    except:  # pragma: no cover
        return False
    else:
        return True


def get_user(username, _config):
    user = dict()
    user["ldap"] = get_user_ldap(username, _config)
    user["swt"] = get_user_swt(username)
    return user


def prepare_request(config, controllers):
    """
     logger is configured to only log error level and above to a file, so the following won't log
     controllers._logger.info(\"\"\"{} {} \"\"\".format(request.path, request.method))
     unless log level is adjusted.
     instead use stdout redirect to a file (supervisor's log, or docker redirect in CMD)
    """
    request.controllers = controllers
    no_token = False
    p = re.compile("|".join(AUTHORIZED_PATHS))
    if p.match(request.path) or request.method == "OPTIONS":  # chrome does not send header to options method
        no_token = True
    headers = request.headers
    if not no_token:
        try:
            try:
                token = headers["Authorization"]
            except KeyError:  # pragma: no cover
                try:
                    token = headers["Authtoken"]
                except KeyError as e:
                    controllers._logger.error(e, exc_info=True)
                    return json.dumps({"title": "Unauthorized",
                                       "description": "Unauthorized",
                                       "error": "Unauthorized"}), 412
            token = token.split()[-1]  # remove 'Bearer'
            token_payload = authenticate(token, config.get("jwt", "secret"))
            if not token_payload:
                return json.dumps({}), 401
        except Exception as e:  # pragma: no cover
            controllers._logger.error(e, exc_info=True)
            return json.dumps({"title": "error validating token",
                               "description": "error validating token",
                               "error": "error validating token"}), 412
        else:
            g._db = db.connect(host=config.get("MySql", "host"),
                               user=config.get("MySql", "user"),
                               passwd=config.get("MySql", "passwd"),
                               port=int(config.get("MySql", "port")),
                               db=config.get("MySql", "db"))

            decoded_token = jwt.decode(token, config.get("jwt", "secret"), algorithms=['HS256'])
            g.username = decoded_token.get("username")
            request.user = get_user(decoded_token.get("username"), config)
            user_groups = request.user.get("ldap", {}).get("groups", {}) if request.user.get("ldap", {}).get("groups") else {}
            try:
                user_digs = list(map(lambda x: x.split("-CoreAdmin")[0],
                                filter(lambda x: "coreadmin" in x.lower(), user_groups.keys())))
            except Exception as e:  # pragma: no cover
                controllers._logger.error(e, exc_info=True)
                raise ApiPreconditionFailedException(description="Error getting CoreAdmin")
            with g._db.cursor() as cursor:
                query = """ SELECT digs_core_number, digs_core_name
                            FROM {}.Digs;
                """.format(config.get("MySql", "db"))
                try:
                    cursor.execute(query)
                except Exception:  # pragma: no cover
                    raise ApiSqlException()
                else:
                    columns = [field[0] for field in cursor.description]
                    res = []
                    for row in cursor:
                        res.append({k: v for k, v in zip(columns, row)})

                    digs = {x["digs_core_name"]: x["digs_core_number"] for x in res}

                user_digs_dict = {v:k for k, v in digs.items() if k in user_digs}
                request.user["digs"] = user_digs_dict

    else:
        g._db = db.connect(host=config.get("MySql", "host"),
                           user=config.get("MySql", "user"),
                           passwd=config.get("MySql", "passwd"),
                           port=int(config.get("MySql", "port")),
                           db=config.get("MySql", "db"))


def prepare_response(response):
    try:
        status_c = int(response.status)
    except Exception:
        status_c = int(response.status_code)
    try:
        g._db.close()
    except:  # pragma: no cover
        pass  # no db connection to close
    try:
        r = make_response(json.dumps(json.loads(response.data.decode("utf-8").strip())),
                          status_c)
    except Exception: #json.decoder.JSONDecodeError:  # pragma: no cover
        r = make_response(json.dumps(str(response.data.decode("utf-8").strip())), status_c)

    r.headers['Access-Control-Allow-Origin'] = "*"
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, PATCH'
    r.headers['Access-Control-Allow-Headers'] = "Content-Type, Access-Control-Allow-Headers, Authorization, authtoken, AuthToken, HTTP_AUTHTOKEN, X-Requested-With"
    r.headers["Content-type"] = "application/json"
    r.headers["Access-Control-Allow-Credentials"] = 'true'
    r.headers["Accept"] = "*/*"
    return r
