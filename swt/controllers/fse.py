import sys

from flask import g

from swt.constants import DIGS_TERMINAL_REQUEST_STATUSES
from swt.exceptions.api_expections import ApiPreconditionFailedException, ApiSqlException
from swt.scripts import usps_shipping
from ._controller import ModelControllerFactory as _controller


class FSE(_controller):
    """Facility Selection Engine
    Rank possible digs facilities (based on shipping cost, or capacity) that can handle the requested sequencing job
    """

    def __init__(self, *args):
        super(FSE, self).__init__(*args)

    @staticmethod
    def get_possible_digs(cursor, db_name, sequencing_tech, post_seq_analysis):
        """ Get active digs facilities, their capacity, and initialize the response dictionary with the
        active digs facilities

        Args:
         sequencing_tech (list): sequencing technology requested for the sequencing job
         post_seq_analysis (list): list of post sequencing analysis to perform

        Returns:
             tuple: (list, dict, dict, list)
        """
        possible_digs, possible_digs_capacity, response, all_ids, full_list = [None] * 5

        cursor.execute("""SELECT * FROM `{}`.`Digs_Capacity` WHERE `active` LIKE 1""".format(db_name))
        columns = [field[0] for field in cursor.description]
        digs_capacity = []
        for row in cursor:
            column_value = (list(zip(columns, row)))
            v = [{k: v for k, v in column_value}][0]
            digs_capacity.append(v)

        """Digs with capacity > 0 and has requested instruments; In a few steps available capacity (total -
        current_number_requests) will be taken into consideration"""
        possible_digs = [dig for dig in digs_capacity if
                         any(list(map(lambda instrument: instrument in dig.get("instruments_operational"),
                                      sequencing_tech)))
                         and all(list(map(lambda capability: capability in
                                                             (dig.get("post_seq_capabilities", " ")
                                                              + ", Consensus Sequence"), post_seq_analysis)))
                         and dig.get("capacity_total") > 0]

        if not possible_digs:
            return possible_digs, possible_digs_capacity, response, all_ids, full_list

        possible_digs_capacity = [{'digs_id': v['digs_id'], 'capacity_total': v['capacity_total']}
                                  for v in possible_digs]

        full_list = ["DIGS-" + str(digs.get("digs_id")) for digs in digs_capacity]
        response = {str(digs.get("digs_id")): None for digs in digs_capacity}
        response["0"] = None  # 0 hold non-available digs to the user request

        all_ids = [dig['digs_id'] for dig in digs_capacity]

        return possible_digs, possible_digs_capacity, response, all_ids, full_list

    def digs_current_usage(self, cursor, db_name):
        """ Get the current available capacity of each digs facility

        Args:
            cursor (pymysql.cursors.Cursor): The cursor to execute the query
            db_name (str): the database name

        Returns:
            list: [{'current_requests': <int>, 'digs_id': <int>}]
        """

        query = """SELECT COUNT(*) as current_requests, r.digs_id
                   FROM {}.Extracts as e
                   JOIN {}.Requests as r
                   on e.request_id=r.id
                   WHERE LCASE(e.status) NOT IN ({})
                   GROUP BY r.digs_id """.format(db_name, db_name, DIGS_TERMINAL_REQUEST_STATUSES)
        try:
            cursor.execute(query)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise ApiSqlException(title="Failed to select sequencing facility",
                                  description=str(e),
                                  logger=self._logger,
                                  config=self._config,
                                  stacktrace=exc_value)

        columns = [field[0] for field in cursor.description]
        digs_requests = []
        for row in cursor:
            column_value = (list(zip(columns, row)))
            digs_requests.append([{k: v for k, v in column_value}][0])
        return digs_requests

    @staticmethod
    def get_candidate_facilities(digs_requests, possible_digs_capacity, number_extracts):
        """ Get list of candidate facilities with enough capacity to handle the job and sequencing tech requested

        Args:
            digs_requests (list): [{'current_requests': <int>, 'digs_id': <int>}]
            possible_digs_capacity (list): [{'digs_id': <int>, 'capacity_total': <int>}]
            number_extracts (int): The number of sequencing extracts being requested

        Returns:
            list: list of ids of candidate facilities

        """
        for v in digs_requests:
            for w in possible_digs_capacity:
                if w['digs_id'] == v['digs_id']:
                    w['current_capacity'] = w['capacity_total'] - v['current_requests']
        candidates = [v for v in possible_digs_capacity if v['current_capacity'] >= number_extracts]
        candidates_id = [v['digs_id'] for v in candidates]
        return candidates_id, candidates

    def get_digs_info(self, cursor, db_name):
        """ Get relavant information for the digs facilities
        Args:
            cursor (pymysql.cursors.Cursor): The cursor to execute the query
            db_name (str): the database name

        Returns:
            dict: id, digs_core_number, contact_email, shipping_adddress_zip for each digs id
        """
        query = """SELECT id, digs_core_number, digs_core_name, contact_name, contact_email, contact_phone,
                    shipping_address_street, shipping_address_city, shipping_address_state, shipping_address_zip
                    FROM `{}`.`Digs`
                   """ \
            .format(db_name)

        try:
            cursor.execute(query)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise ApiSqlException(title="Failed to select sequencing facility",
                                  description=str(e),
                                  logger=self._logger,
                                  config=self._config,
                                  stacktrace=exc_value)

        columns = [field[0] for field in cursor.description]
        digs_info_ = []
        digs_info = {}
        for row in cursor:
            column_value = (list(zip(columns, row)))
            digs_info_.append(column_value)

        for digs in digs_info_:
            d = dict(digs)
            digs_info[d.get("id")] = d

        return digs_info

    @staticmethod
    def get_shipping_cost_to_each_facility(digs_info, candidates_id, zipcode):
        """calculate shipping cost to each available facility

        Args:
            digs_info (dict): relevant fields of each digs
            candidates_id (list):  list of possible digs for the job
            zipcode (str | int): user's origin zipcode

        Returns:
            dict: {<id>: <cost>}
        """
        cost = {}
        for _id in candidates_id:
            destzip = digs_info[_id].get("shipping_address_zip").split("-")[0]

            try:
                rate = usps_shipping(dest_zip=destzip, origin_zip=zipcode)
            except Exception:
                raise ApiPreconditionFailedException(
                    description="can't calculate shipping rate. Check that the zipcode is valid")
            else:
                cost[_id] = rate
        return cost

    def create_response(self, candidates_id, cursor, response, all_ids, full_list, db_name, zipcode, country,
                        candidates):
        """ Build the response object

        Args:
            candidates_id (list): list of candidate facility ids (a subset of all the ids)
            cursor (pymysql.cursors.Cursor): The cursor to execute the query
            response (dict): the initialized response object
            all_ids (list): list of the ids of all facilities
            full_list (list): list of DIGS-<ID>   ['DIGS-1', 'DIGS-2', 'DIGS-3', 'DIGS-4', 'DIGS-5', 'DIGS-6']
            db_name (str): the database name
            zipcode (str | int): origin zipcode

        Returns:
            dict: the response object
        """

        digs_info = self.get_digs_info(cursor, db_name)

        if len(candidates_id) == 0:
            """Note: Code does not reach here.
            If no available facilities to take the job, an exception is raised earlier"""
            response["0"] = full_list
            response["1"] = []
            response_c = response.copy()
            response = {key: response_c[key] for key in response_c if response_c[key] is not None}
        elif len(candidates_id) == 1:
            response["0"] = full_list
            response["1"] = "DIGS-" + str(candidates_id[0])
            response_c = response.copy()
            response_c["0"].remove(response["1"])
            response = {key: response_c[key] for key in response_c if response_c[key] is not None}
        else:
            cost = self.get_shipping_cost_to_each_facility(digs_info, candidates_id,
                                                           zipcode) if country == "USA" else {}

            if not any(cost.values()):
                unavailable_digs_ids = list(set(all_ids))  # list(set(all_ids) - set(cost))
                # unavailable_digs = ["DIGS-" + str(i) for i in unavailable_digs_ids]
                # response["0"] = [] #unavailable_digs
                sorted_cap = sorted(candidates, key=lambda k: k['current_capacity'], reverse=True)
                for i, cap in enumerate(sorted_cap):
                    response[str(i + 1)] = "DIGS-" + str(cap['digs_id'])
                    unavailable_digs_ids.remove(cap['digs_id'])
                response["0"] = ["DIGS-" + str(i) for i in unavailable_digs_ids]
            else:
                sort_c = sorted(cost, key=cost.__getitem__)
                unavailable_digs_ids = list(set(all_ids) - set(sort_c))
                unavailable_digs = ["DIGS-" + str(i) for i in unavailable_digs_ids]
                response["0"] = unavailable_digs
                sort_c += ['None'] * (len(full_list) - len(cost))
                for i, cost in enumerate(sort_c):
                    response[str(i + 1)] = "DIGS-" + str(cost)
                response = {key: response[key] for key in response if response[key] != "DIGS-None"}

        response["contact_email"] = {digs_info[contact].get("digs_core_number"): digs_info[contact].get("contact_email")
                                     for contact in digs_info}
        response["contact_info"] = {
            digs_info[contact].get("digs_core_number"): {'core': digs_info[contact].get("digs_core_name"),
                                                         'email': digs_info[contact].get("contact_email"),
                                                         'name': digs_info[contact].get("contact_name"),
                                                         'phone': digs_info[contact].get("contact_phone"),
                                                         'address_street': digs_info[contact].get("shipping_address_street"),
                                                         'address_rest': "{}, {} {}".format(
                                                             digs_info[contact].get("shipping_address_city"),
                                                             digs_info[contact].get("shipping_address_state"),
                                                             digs_info[contact].get("shipping_address_zip"))
                                                         }
            for contact in digs_info}

        return response

    def select_facility(self, zipcode, country, number_extracts, sequencing_tech, post_seq_analysis):
        """Get ranked digs facilities for the sequencing job

        Args:
            zipcode (str|int): the origin zipcode
            country (str): the origin country
            number_extracts (int): the number of extracts being sequenced
            sequencing_tech (list): list of sequencing technologies requested

        Returns:
            dict: the response object

        Raises:
            ApiPreconditionFailedException

        """

        conn = g._db
        db_name = self._config.get("MySql", "db")

        response = None
        with conn.cursor() as cursor:
            try:
                # possible_digs: has requested tech
                # possible_digs_capacity: capacity of the facilities with required tech
                possible_digs, possible_digs_capacity, response, all_ids, full_list = \
                    self.get_possible_digs(cursor,
                                           db_name,
                                           sequencing_tech, post_seq_analysis)

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ApiPreconditionFailedException(
                    title="Facility Selection failed",
                    description="No facility available with sequencing capacity for the requested instruments",
                    logger=self._logger,
                    config=self._config,
                    stacktrace=exc_value)

            if not possible_digs:
                raise ApiPreconditionFailedException(
                    title="No facility available with sequencing capacity for the requested instruments",
                    description="No facility available with sequencing capacity for the requested instruments",
                    logger=self._logger,
                    config=self._config)
            try:
                digs_requests = self.digs_current_usage(cursor, db_name)
                with_requests = [int(x["digs_id"]) for x in digs_requests]
                digs_requests += [{'current_requests': 0, 'digs_id': x} for x in all_ids if x not in with_requests]
                candidates_id, candidates = self.get_candidate_facilities(digs_requests, possible_digs_capacity,
                                                                          number_extracts)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ApiPreconditionFailedException(
                    title="Facility Selection failed",
                    description="No facility has sequencing capacity to accept your request at this time",
                    logger=self._logger,
                    config=self._config,
                    stacktrace=exc_value)

            if not candidates_id:
                raise ApiPreconditionFailedException(
                    title="No facility has sequencing capacity to accept your request at this time",
                    description="No facility has sequencing capacity to accept your request at this time",
                    logger=self._logger,
                    config=self._config)

            response = self.create_response(candidates_id, cursor, response, all_ids, full_list, db_name, zipcode,
                                            country, candidates)

        if not response:
            raise ApiPreconditionFailedException(
                title="Facility Selection failed",
                description=str(e),
                logger=self._logger,
                config=self._config)
        return response

    @staticmethod
    def validate_zipcode(destzip, origin_zipcode=11215):
        """Validate a zipcode.

        Args:
            destzip (str | int):  the destination zipcode
            origin_zipcode (str | int):  the origin zipcode:

        Returns:
            Bool: True if shipping rate can be calculated

        Raises:
            ApiPreconditionFailedException if zipcode is invalid format or non-existent
        """
        try:
            res = usps_shipping(dest_zip=destzip, origin_zip=origin_zipcode)
        except Exception as e:
            """Only raises exception if usps returns an error in the xml. If it can't communicate, returns None
            """
            raise ApiPreconditionFailedException(title="Invalid Zipcode", description=str(e))
        if not res:
            pass  # let validation pass, FSE will use a different criteria if it can't validate the zipcode
            # raise ApiPreconditionFailedException(title="Invalid Zipcode", description=e)
        return True
