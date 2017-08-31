from ._controller import ModelControllerFactory as _controller
from flask import g, request
from swt.constants import DIGS_TERMINAL_REQUEST_STATUSES
from swt.exceptions.api_expections import ApiSqlException, ApiException, ApiPreconditionFailedException


class Digs(_controller):
    """Get Information about a Digs facility (capacity, contact, current usage)

    """

    def __init__(self, *args):
        super(Digs, self).__init__(*args)

    @staticmethod
    def execute_query(query, cursor):
        try:
            res = cursor.execute(query)
        except Exception as e:
            raise ApiSqlException(description=e)
        else:
            if res:
                row = cursor.fetchone()
                if row:  # only if select. If insert, there's no row
                    columns = [field[0] for field in cursor.description]
                    return {k: v for k, v in zip(columns, row)}
                else:  # insertions
                    return res  # 1 if inserted, 0 if the value was the same and did not insert)
        return {}

    def get_current_usage(self, digs_core_name, cursor, db_name):
        """ Get current usage
        """
        query = """SELECT Count(*) as count, r.digs_id
                   FROM `{db_name}`.`Extracts` AS e
                   JOIN `{db_name}`.`Requests` AS r
                   ON e.request_id = r.id
                   WHERE LCASE(e.status) NOT IN({statuses})
                   AND r.digs_id = (SELECT `id`
                                    FROM `{db_name}`.`Digs`
                                    WHERE `digs_core_name`
                                    LIKE '{digs_core_name}')
                   GROUP BY r.digs_id
                   """.format(db_name=db_name, digs_core_name=digs_core_name, statuses=DIGS_TERMINAL_REQUEST_STATUSES)
        return self.execute_query(query, cursor)

    def get_digs_contact(self, digs_core_name, cursor, db_name):
        """Get Digs Contact
        """
        query = """SELECT * FROM `{db_name}`.`Digs`
                   WHERE `digs_core_name` LIKE '{digs_core_name}'""".format(db_name=db_name,
                                                                            digs_core_name=digs_core_name)
        return self.execute_query(query, cursor)

    def get_digs_capacity(self, digs_core_name, cursor, db_name):
        """ Get Digs Capacity
        """
        query = """SELECT * FROM `{db_name}`.`Digs_Capacity`
                    WHERE `digs_id`
                    LIKE (SELECT `id`
                         FROM `{db_name}`.`Digs`
                         WHERE `digs_core_name`
                         LIKE '{digs_core_name}')""".format(db_name=db_name, digs_core_name=digs_core_name)
        return self.execute_query(query, cursor)

    def get_digs_by_id(self, user, digs_facility_name):
        conn = g._db
        db_name = self._config.get("MySql", "db")
        core_admin = user.get("digs")

        if digs_facility_name not in core_admin.values():
            return {"status": False, "statusText": "User not in Requested Core group"}

        with conn.cursor() as cursor:
            try:
                count_res = self.get_current_usage(digs_facility_name, cursor, db_name)
                digs_current_usage = int(0 if not count_res else count_res.get("count"))
            except Exception as e:
                self._logger.error("failed to get digs facility's current usage")
                raise ApiPreconditionFailedException(description="failed to get digs facility's current usage", title="API error")

            digs_contact = self.get_digs_contact(digs_facility_name, cursor, db_name)
            if not digs_contact:
                self._logger.error("failed to get digs facility's contact")
                raise ApiPreconditionFailedException(description="failed to get digs facility's contact", title="API error")
            digs_contact["modified"] = None
            digs_capacity = self.get_digs_capacity(digs_facility_name, cursor, db_name)

            if not digs_capacity:
                self._logger.error("failed to get digs facility's capacity")
                raise ApiPreconditionFailedException(description="failed to get digs facility's capacity", title="API error")
            digs_capacity["start_date"] = None  # json can't serialize datetime, and it's not used by the FE
            digs_capacity["created"] = None  # json can't serialize datetime, and it's not used by the FE
            digs_capacity["modified"] = None  # json can't serialize datetime, and it's not used by the FE

            return {"current_usage": digs_current_usage, "contact": digs_contact, "capacity": digs_capacity}

    def update_digs(self, user, digs_facility_name, update_params):
        conn = g._db
        db_name = self._config.get("MySql", "db")
        core_admin = user.get("digs")

        if digs_facility_name not in core_admin.values():
            raise ApiPreconditionFailedException(title="User not in Requested Core group", description="User not in Requested Core group",
                               logger=self._logger, config=self._config)

        with conn.cursor() as cursor:
            digs_contact = self.get_digs_contact(digs_facility_name, cursor, db_name)
            res = False

            if not digs_contact:
                raise ApiPreconditionFailedException(description="failed to get digs facility's contact for mysql id", title="API error",
                                   logger=self._logger, config=self._config)
            id_ = digs_contact.get("id")
            if not id_:
                raise ApiPreconditionFailedException(description="failed to get id from digs facility's contact", title="API error",
                                   logger=self._logger, config=self._config)

            if update_params["name"] == "capacity":
                capacity = int(update_params["params"]["value"])
                query = """UPDATE `{db_name}`.`Digs_Capacity`
                            SET `capacity_total` = {capacity}
                            WHERE `digs_id` = {id_}""".format(db_name=db_name, capacity=capacity, id_=id_)
                res = self.execute_query(query, cursor)
                conn.commit()

            elif update_params["name"] == "toggle_propagation_month_to_month":
                digs_capacity = self.get_digs_capacity(digs_facility_name, cursor, db_name)
                propagate_month_to_month = bool(digs_capacity.get("propagate_month_to_month"))
                propagate_month_to_month = 0 if propagate_month_to_month else 1

                query = """UPDATE `{db_name}`.`Digs_Capacity`
                            SET `propagate_month_to_month` = {propagate_month_to_month}
                            WHERE `digs_id` = {id_}""".format(db_name=db_name,
                                                              propagate_month_to_month=propagate_month_to_month,
                                                              id_=id_)
                res = self.execute_query(query, cursor)
                conn.commit()

            elif update_params["name"] == "instrument":
                instrument = update_params["params"]["instrument"]
                checked = update_params["params"]["checked"]

                query = """SELECT `instruments_operational`
                           FROM `{db_name}`.`Digs_Capacity`
                           WHERE `digs_id` = {id_}""".format(db_name=db_name, id_=id_)

                res = self.execute_query(query, cursor)
                old_instruments = res["instruments_operational"].split(",") if res["instruments_operational"] else []
                old_instruments.append(instrument) if checked else (
                    old_instruments.remove(instrument) if instrument in old_instruments else old_instruments)
                new_instruments = ",".join(set(old_instruments))
                query = """UPDATE `{db_name}`.`Digs_Capacity`
                            SET `instruments_operational` = "{new_instruments}"
                            WHERE `digs_id` = {id_}""".format(db_name=db_name, new_instruments=new_instruments, id_=id_)
                res = self.execute_query(query, cursor)
                conn.commit()

            elif update_params["name"] == "postSeqCap":
                capability = update_params["params"]["capability"]
                checked = update_params["params"]["checked"]

                query = """SELECT `post_seq_capabilities`
                           FROM `{db_name}`.`Digs_Capacity`
                           WHERE `digs_id` = {id_}""".format(db_name=db_name, id_=id_)

                res = self.execute_query(query, cursor)
                old_capabilities = res["post_seq_capabilities"].split(",") if res["post_seq_capabilities"] else []
                old_capabilities.append(capability) if checked else (
                    old_capabilities.remove(capability) if capability in old_capabilities else old_capabilities)
                new_capabilities = ",".join(set(old_capabilities))
                query = """UPDATE `{db_name}`.`Digs_Capacity`
                            SET `post_seq_capabilities` = "{post_seq_capabilities}"
                            WHERE `digs_id` = {id_}""".format(db_name=db_name, post_seq_capabilities=new_capabilities,
                                                              id_=id_)
                res = self.execute_query(query, cursor)
                conn.commit()

            if not res:
                raise ApiSqlException(title="Server Error",
                                      description="Failed to update {} with {}".format(digs_facility_name,
                                                                                       update_params["name"]),
                                      logger=self._logger, config=self._config)
            return True
