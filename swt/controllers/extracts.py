from ._controller import ModelControllerFactory as _controller
from flask import g, request
from swt.exceptions.api_expections import ApiSqlException, ApiUnauthorizedOperationException, ApiException, \
    ApiPreconditionFailedException
import json
import boto.ses
from ..util.s3 import S3
import requests
from tempfile import SpooledTemporaryFile
import zipfile
from uuid import uuid4
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from swt.constants import EXTRACT_EMAIL_FACILITY_SUBJECT, EXTRACT_EMAIL_FACILITY_BODY, \
    EXTRACT_EMAIL_REQUESTER_SUBJECT, EXTRACT_EMAIL_REQUESTER_BODY, EXTRACT_EMAIL_SIGNATURE


class Extracts(_controller):
    def __init__(self, *args):
        super(Extracts, self).__init__(*args)

    def zip_multi_seq(self, _files):
        bucket = self._config.get("aws", "s3_bucket")
        sequence_zip_filefolder = self._config.get("aws", "s3_sequence_zip_filefolder")
        aws_configuration = {
            'aws_access_key_id': self._config.get('aws', 'aws_access_key_id'),
            'aws_secret_access_key': self._config.get('aws', 'aws_secret_access_key'),
            'region_name': self._config.get('aws', 'aws_region')
        }

        _s3 = S3(credentials=aws_configuration, logger=self._logger)

        with SpooledTemporaryFile() as fh:
            with zipfile.ZipFile(fh, 'w') as myzip:
                for url in _files:
                    url = url.strip()
                    url = url[5:] if url.startswith("s3") else url
                    fname = url.split("/")[-1]
                    req = requests.get(url)
                    if req.status_code < 400:
                        res = req.text
                        myzip.writestr(fname, res, )
            fh.seek(0)
            key = "{}/{}.zip".format(sequence_zip_filefolder, str(uuid4()))

            pre_signed_url = _s3.upload(bucket, key, fh)

        return pre_signed_url

    def get_sequence_url_of_extract(self, extracts, cursor, db_name):

        ometa_key = self._config.get("ometa", "key")
        api_base_url = self._config.get("api", "origin")

        incomplete = "+".join([extract["extract_id"] for extract in extracts if extract["status"] != "Completed"])

        if not incomplete:
            return False

        query = "{}/solr/consensus_sequence/select?q=*%3A*&fq=extract_identifier%3A({})&fl=file_name%2C+extract_identifier%2C+sample_identifier%2C+sample_id&wt=json".format(
            self._config.get("solr", "url"), incomplete)

        r = requests.get(query)

        if r.status_code < 400:
            resp = r.json()
            n_res = int(resp.get("response", {}).get("numFound", 0))
            seqs = resp.get("response", {}).get("docs", [])
            for seq in seqs:
                _files = seq.get("file_name").split(",")
                if len(_files) > 1:
                    try:
                        url = self.zip_multi_seq(_files)
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        raise ApiSqlException(title="Application Error", description=str(e),
                                              logger=self._logger, config=self._config, stacktrace=exc_value)
                else:
                    url = _files[0]

                url = url[5:] if url.startswith("s3://") else url  # this can be removed

                query = """UPDATE `{}`.`Extracts`
                           SET `status`="Completed", `results`="{}"
                           WHERE `extract_id` LIKE '{}';""".format(db_name, url, seq.get("extract_identifier"))
                try:
                    cursor.execute(query)
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    raise ApiSqlException(title="Application Error", description=str(e),
                                          logger=self._logger, config=self._config, stacktrace=exc_value)
                else:
                    sample_id = seq.get("sample_id")
                    query = "{}/ometa/swtupdate.action?apiKey={}&sampleIds={}&status=Completed".format(api_base_url,
                                                                                                       ometa_key,
                                                                                                       sample_id)
                    updated_ometa = False
                    status_code = None
                    success = False
                    status = False
                    try:
                        r = requests.get(query)
                        status_code = r.status_code
                        resp = r.json()
                        success = resp.get("results")
                        status = resp.get("status")
                        updated_ometa = True
                    except Exception:
                        updated_ometa = False
                    if not all([updated_ometa, status_code == 200, success == "success", status == "Completed"]):
                        error_msg = "failed to update ometa status for extract id: {} / sample_id: {}".\
                            format(seq.get("extract_identifier"), sample_id)
                        raise ApiPreconditionFailedException(title=error_msg,
                                                             description=error_msg,
                                                             logger=self._logger,
                                                             config=self._config)
            return n_res
        return False

    def _get_extracts(self, user, cursor):
        db_name = self._config.get("MySql", "db")
        core_admin = user.get("digs")
        extracts = []
        requestNumbers = set()
        requesters_ = set()
        base_query = """SELECT
                          Extracts.id,
                          Requests.id as request_id,
                          Requests.requester,
                          Requests.digs_id,
                          Requests.institution,
                          Extracts.extract_id,
                          Digs_.digs_core_name AS digs,
                          Extracts.results,
                          Extracts.status
                        FROM {}.Extracts AS Extracts
                        JOIN {}.Requests AS Requests
                          ON Extracts.request_id = Requests.id
                        JOIN {}.Digs AS Digs_
                          ON Requests.digs_id = Digs_.id
                        WHERE
        """.format(db_name, db_name, db_name, db_name)

        if core_admin:
            where_query = """{}.Requests.digs_id IN (SELECT
                          id
                        FROM {}.Digs as Digs_
                        WHERE digs_core_number IN (\"{}\"))""". \
                format(db_name, db_name, "\",\"".join(core_admin.keys()))
        else:
            where_query = """ Requests.requester LIKE \"{}\"""".format(user.get("ldap", {}).get("actor_username"))

        try:
            cursor.execute(base_query + where_query)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise ApiSqlException(title=str(e), description=str(e),
                                  logger=self._logger, config=self._config, stacktrace=exc_value)
        else:
            columns = [field[0] for field in cursor.description]
            for row in cursor:
                r = {k: v for k, v in zip(columns, row)}
                extracts.append(r)
                requesters_.add(r.get("requester"))
                try:
                    requestNumbers.add(int(r.get("extract_id").split("_")[0][1:]))
                except:
                    pass
        return extracts, requesters_, requestNumbers

    def get_extracts(self, user):
        # raise ApiPreconditionFailedException(title="oops", description="OK NO")
        conn = g._db
        db_name = self._config.get("MySql", "db")
        core_admin = user.get("digs")

        resp = {"status": True, "core": bool(core_admin), "requesters": [], "requestNumbers": [], "extracts": [],
                "digs": core_admin}
        requesters_dict = {}
        requesters = []

        with conn.cursor() as cursor:

            extracts, requesters_, requestNumbers = self._get_extracts(user, cursor)

            recent_requests = {}

            for r in extracts:
                if r["request_id"] not in recent_requests:
                    recent_requests[r["request_id"]] = {"completed": 0, "in_progress": 0}

                if r["status"].lower() == "completed":
                    recent_requests[r["request_id"]]["completed"] += 1
                elif r["status"] not in ["Failed-Samples Not Received",
                                         "Failed-Sample QC", "Failed-Sequencing/Assembly", "Declined"]:
                    recent_requests[r["request_id"]]["in_progress"] += 1
                else:
                    del recent_requests[r["request_id"]]

            """
            Get list of most recent requests for chart in landing page
            """
            most_recent_requests_keys = sorted(list(recent_requests.keys()))[-4:]
            most_recent_requests = {}

            for key in recent_requests:
                if key in most_recent_requests_keys:
                    total = recent_requests[key]["completed"] + recent_requests[key]["in_progress"]
                    percentage = {
                        "completed": int(100 * recent_requests[key]["completed"] / float(total)),
                        "in_progress": int(100 * recent_requests[key]["in_progress"] / float(total)),
                        "nsamples": total
                    }
                    most_recent_requests[key] = percentage

            resp["most_recent_requests"] = most_recent_requests

            update_sequencing_results = self.get_sequence_url_of_extract(extracts, cursor, db_name)
            conn.commit()
            if update_sequencing_results:
                extracts, requesters_, requestNumbers = self._get_extracts(user, cursor)

            for requester in requesters_:
                try:
                    user = self.user.get_user(requester, swt=False, ldap=True)  # TODO: cache this
                except ApiPreconditionFailedException:
                    user[
                        "ldap"] = {}  # If requester does not exist in ldap (e.g. request from an old user that has been deleted from ldap)
                first_last_name = "{} {}".format(user.get("ldap", {}).get("actor_first_name", requester),
                                                 user.get("ldap", {}).get("actor_last_name", requester))
                requesters_dict[requester] = first_last_name
                requesters.append(first_last_name)
            resp["requesters"] = {requester_n: False for requester_n in list(requesters)}
            resp["requestNumbers"] = list(map(lambda x: ("R" + str(x)), sorted(requestNumbers)))

            for extract in extracts:
                extract["requester"] = requesters_dict[extract["requester"]]
            resp["extracts"] = extracts

        return resp

    def insert_extracts(self, user, payload):
        """Insert multiple extracts into the database, as a single request

        :param user:
        :param payload:
        :return:
        """
        conn = g._db
        db_name = self._config.get("MySql", "db")
        env = self._config.get("api", "env")
        cor_admin = user.get("digs")

        # self._logger.error("oopies")

        user_info = payload.get("user")
        samples = payload.get("samples")
        facility = payload.get("facility")
        manifesto = payload.get("manifesto")
        institution = user.get("ldap", {}).get("actor_institution")
        request_uid = str(uuid4())

        # create array of choices to insert into database
        # this is only for tracking the options presented purposes (possible debugging),
        # since only facility.get("choice") is critical information
        fse_choices = facility.get("digs")
        fse = []
        for key in fse_choices:
            try:
                rank = int(key)
            except:
                pass
            else:
                fse.append(fse_choices[str(rank)])

        request_id = None
        emailed = None

        # Create request
        query = """INSERT INTO `{}`.`Requests` (`uid`, `digs_id`, `fse`, `requester`, `institution`, `created` )
                  VALUES (\"{}\", (SELECT id from `{}`.`Digs` WHERE digs_core_number LIKE \"{}\"), \'{}\', "{}", \"{}\", NOW())""" \
            .format(db_name, request_uid, db_name, facility.get("choice"), json.dumps(fse),
                    user.get("ldap", {}).get("actor_username"), institution)

        with conn.cursor() as cursor:
            try:
                cursor.execute(query)
                conn.commit()
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ApiSqlException(title=str(e), description=str(e),
                                      logger=self._logger, config=self._config, stacktrace=exc_value)
            else:
                query = """SELECT id from `{}`.`Requests` WHERE `uid` LIKE '{}'""".format(db_name, request_uid)
                try:
                    cursor.execute(query)
                    columns = [field[0] for field in cursor.description]
                    res = cursor.fetchone()
                    if res:
                        request = dict(zip(columns, [res[0]]))
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    raise ApiSqlException(title=str(e), description=str(e),
                                          logger=self._logger, config=self._config, stacktrace=exc_value)
                else:
                    request_id = request.get("id")

            selected_facility = None
            query = """SELECT * FROM `{}`.`Digs` WHERE `digs_core_number` LIKE '{}'""".format(db_name, facility.get("choice"))
            try:
                cursor.execute(query)
                columns = [field[0] for field in cursor.description]
                res = cursor.fetchone()
                if res:
                    selected_facility = dict(zip(columns, res))
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ApiSqlException(title=str(e), description=str(e),
                                      logger=self._logger, config=self._config, stacktrace=exc_value)

            csv_manifest = []
            res_manifesto = []
            if request_id:
                csv_manifest.append('DIGS Sequencing Request Submission ID: R{}\n\n'.format(request_id))
                # requester info block
                csv_manifest.append('Requester Contact Information\n')
                csv_manifest.append('Name,{}\n'.format(user_info.get("name")))
                csv_manifest.append('Address,"{}, {} {} {}"\n'.format(
                    user_info.get("street_address"),
                    user_info.get("city"),
                    user_info.get("state_province") if user_info.get("state_province") != "N/A" else "",
                    selected_facility.get("zipcode")))
                csv_manifest.append('Phone,{}\n'.format(user_info.get("daytime_phone")))
                csv_manifest.append('Email,{}\n\n'.format(user_info.get("email")))
                # facility info block
                csv_manifest.append('DIGS Facility Contact Information\n')
                csv_manifest.append('Name,{}\n'.format(selected_facility.get("contact_name")))
                csv_manifest.append('Address,"{}, {} {} {}"\n'.format(
                    selected_facility.get("shipping_address_street"),
                    selected_facility.get("shipping_address_city"),
                    selected_facility.get("shipping_address_state") if selected_facility.get("shipping_address_state") \
                                                                       != "N/A" else "",
                    selected_facility.get("shipping_address_zip")))
                csv_manifest.append('Phone,{}\n'.format(selected_facility.get("contact_phone")))
                csv_manifest.append('Email,{}\n\n'.format(selected_facility.get("contact_email")))

                # sample table block
                csv_manifest.append("Sample Identifier,Extract Identifier,Sequencing Study Identifier,Submission ID,"
                                    "Submission Type,Submitter Name,Submission Date,Project Identifier,"
                                    "Contributing Institution,Virus Identifier,Strain Name,Influenza Subtype,"
                                    "Host Species,Lab Host,Passage History,Pathogenicity,"
                                    "Extract Material,Volume (µl),Concentration (ng/µl),Concentration Determined By,"
                                    "Sequencing Technology,Analysis Type,Raw Sequences,Comments\n")

                request_contains_rna_sample = False

                for row, sample in enumerate(samples, 12):
                    if sample.get("extract_material") == "Viral RNA":
                        request_contains_rna_sample = True

                    extract_id = "R{}_{}".format(request_id, sample["extract_id"])
                    query = """INSERT INTO `{}`.`Extracts` (`request_id`, `sample_id`, `extract_id`,
                                    `sequencing_study_identifier`, `submission_id`, `submission_type`, `submitter_name`,
                                    `submission_date`, `project_identifier`, `virus_identifier`, `influenza_subtype`,
                                    `host_species`, `lab_host`, `passage_history`, `pathogenicity`, `extract_material`,
                                    `volume`, `concentration`, `concentration_determined_by`, `sequencing_tecnhology`,
                                     `analysis_type`, `raw_sequences`, `comments`, `status`, `created`,
                                     `sample_identifier`)
                                VALUES( {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}',
                                    '{}', '{}', '{}', {}, {}, '{}', '{}', '{}','{}', '{}', 'Requested',
                                    CURRENT_TIMESTAMP, '{}' )""". \
                        format(db_name,
                               request_id,
                               sample.get("sample_id"),
                               extract_id,
                               sample.get("sequencing_study_identifier"),
                               sample.get("submission_id"),
                               sample.get("submission_type"), sample.get("submitter_name"),
                               sample.get("submission_date"),
                               sample.get("project_identifier"),
                               sample.get("virus_identifier"),
                               sample.get("influenza_subtype"),
                               sample.get("host_species"), sample.get("lab_host"),
                               sample.get("passage_history"),
                               sample.get("pathogenicity"),
                               sample.get("extract_material"),
                               sample.get("volume"), sample.get("concentration"),
                               sample.get("concentration_determined_by"),
                               json.dumps(sample.get("sequencing_technology")),
                               json.dumps(sample.get("analysis_type")),
                               sample.get("raw_sequences", '0'),
                               sample.get("comments"),
                               sample.get("sample_identifier"))

                    try:
                        res = cursor.execute(query)
                        if res:
                            conn.commit()
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        raise ApiSqlException(title=str(e), description=str(e),
                                              logger=self._logger, config=self._config, stacktrace=exc_value)
                    else:
                        analysis_type = " / ".join(
                            [analysis for analysis in sample["analysis_type"] if sample["analysis_type"][analysis]])
                        sequencing_technology = " or ".join(
                            [tech for tech in sample["sequencing_technology"] if sample["sequencing_technology"][tech]])
                        csv_manifest.append("\"{}\",\"{}\",\"{}\",\"{}\t\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\","
                                            "\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\","
                                            "\"{}\",\"{}\",\"{}\",\"{}\"\n".format(
                            sample.get("sample_identifier"), extract_id,
                            sample.get("sequencing_study_identifier"), sample.get("submission_id", ""),
                            sample.get("submission_type", ""), sample.get("submitter_name", ""),
                            sample.get("submission_date", ""), sample.get("project_identifier"),
                            sample.get("contributing_institution", ""), sample.get("virus_identifier"),
                            sample.get("strain_name"), sample.get("influenza_subtype"),
                            sample.get("host_species"), sample.get("lab_host"), sample.get("passage_history"),
                            sample.get("pathogenicity"), sample.get("extract_material"),
                            sample.get("volume"), sample.get("concentration"),
                            sample.get("concentration_determined_by"), sequencing_technology, analysis_type,
                            sample.get("raw_sequences", "N"), sample.get("comments", "")))
                        res_manifesto.append([sample.get("sample_identifier"), sample.get("extract_id"),
                            sample.get("sequencing_study_identifier"), sample.get("submission_id", ""),
                            sample.get("submission_type", ""), sample.get("submitter_name", ""),
                            sample.get("submission_date", ""), sample.get("project_identifier"),
                            sample.get("contributing_institution", ""), sample.get("virus_identifier"),
                            sample.get("strain_name"), sample.get("influenza_subtype"), sample.get("host_species"),
                            sample.get("lab_host"), sample.get("passage_history"), sample.get("pathogenicity"),
                            sample.get("extract_material"), sample.get("volume"), sample.get("concentration"),
                            sample.get("concentration_determined_by"), sequencing_technology, analysis_type,
                            sample.get("raw_sequences", "N"), sample.get("comments", "")])

                # wb.save("manifest.xls")
                with SpooledTemporaryFile() as fh:
                    # writer = csv.writer(fh, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                    fh.writelines([x.encode('utf-8') for x in csv_manifest])
                    fh.seek(0)
                # with open("swt/scripts/request_{}.{}".format(request_id, "csv"), 'w') as file:
                #     for line in csv_manifest:
                #         file.write(line)

                    aws_configuration = {
                        'aws_access_key_id': self._config.get('aws', 'aws_access_key_id'),
                        'aws_secret_access_key': self._config.get('aws', 'aws_secret_access_key'),
                        'region_name': self._config.get('aws', 'aws_region')
                    }

                    _s3 = S3(credentials=aws_configuration, logger=self._logger)

                    filename = "request_{}.{}".format(request_id, "csv")
                    bucket = self._config.get("aws", "s3_bucket")
                    # bucket = "swt-prod"
                    key = "manifest-files/" + filename

                    pre_signed_url = _s3.upload(bucket, key, fh)

                    if not pre_signed_url:
                        return {"status": False,
                                "statusText": "Error uploading manifest to aws"}

                    rna_warning_msg = """<br><p><u>Notice</u>: This Sequencing Request includes RNA-based samples.
                        Please handle accordingly when shipping your samples.</p>""" \
                        if request_contains_rna_sample else ""

                    conn = boto.ses.connect_to_region(**aws_configuration)
                    email_from = 'support@niaidceirs.org'

                    user_email = user_info.get("email")
                    facility_email = user_email

                    if env == "prod":
                        facility_email = facility.get("digs", {}).get("contact_info", {})\
                            .get(facility.get("choice")).get("email")


                    email_body_facility = EXTRACT_EMAIL_FACILITY_BODY.format(request_id,
                                                                             user_info.get("name"),
                                                                             "{}, {} {} {}".format(
                                                                                 user_info.get("street_address"),
                                                                                 user_info.get("city"),
                                                                                user_info.get("state_province") \
                                                                                    if user_info.get("state_province") \
                                                                                       != "N/A" else "",
                                                                                 user_info.get("zipcode")),
                                                                             user_info.get("daytime_phone"),
                                                                             user_info.get("email"),
                                                                             EXTRACT_EMAIL_SIGNATURE,
                                                                             rna_warning_msg)
                    emailMsg = MIMEMultipart()
                    emailMsg['Subject'] = EXTRACT_EMAIL_FACILITY_SUBJECT
                    emailMsg['From'] = email_from
                    emailMsg['To'] = facility_email
                    emailMsg.preamble = 'Multipart message.\n'
                    part = MIMEText(email_body_facility, 'html')
                    emailMsg.attach(part)
                    part = MIMEBase('application', 'octet-stream')
                    fh.seek(0)
                    part.set_payload(fh.read())
                    encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment; filename="shipping_manifest.csv"')
                    emailMsg.attach(part)
                    emailed_facility = conn.send_raw_email(emailMsg.as_string(),
                                                           source=emailMsg['From'], destinations=[emailMsg['To']])

                    email_body_requester = EXTRACT_EMAIL_REQUESTER_BODY.format(user_info.get("name"),
                                                                               request_id,
                                                                               pre_signed_url,
                                                                               selected_facility.get(
                                                                                   "digs_core_name"),
                                                                               selected_facility.get(
                                                                                   "digs_core_name"),
                                                                               EXTRACT_EMAIL_SIGNATURE,
                                                                               rna_warning_msg)
                    emailed_requester = conn.send_email(email_from, EXTRACT_EMAIL_REQUESTER_SUBJECT,
                                                        None, to_addresses=user_info.get("email"),
                                                        format="html", html_body=email_body_requester)
                    email_failed = not emailed_facility or not emailed_requester

                    if email_failed:
                        raise ApiSqlException(
                            title="Extracts have been saved, but there was a problem emailing the DIGS facility. Please contact the DPCC",
                            description="Extracts have been saved, but there was a problem emailing the DIGS facility. Please contact the DPCC",
                            logger=self._logger, config=self._config)
                    return {"status": True, "request_id": request_id, "manifesto": res_manifesto}

    def update_extract(self, user):
        """ Generic update of any extract field

        :param user:
        :return:
        """
        pass

    def update_status(self, user, payload=None):
        """payload comes comes in as Multidict, wich converts nicely to dict, except lists are serialized funny:
        {'extract_row_id': ['12'], 'name': ['status'], 'value': ['Requested'], 'extracts_to_update_status[0]': ['6'], 'extracts_to_update_status[1]': ['12'], 'extracts_to_update_status[2]': ['13'], 'extracts_to_update_status[3]': ['14']}

        payload must be parsed for items that are of type list

        :param user:
        :param payload:
        :return:
        """

        id_ = int(payload.get("extract_row_id"))

        cor_admin = user.get("digs")
        if not cor_admin:
            self._logger.warning("Non-admin user cannot modify request status: {}".format(user))

            raise ApiUnauthorizedOperationException(title="Non-admin user cannot modify request status",
                                                    description="Non-admin user cannot modify request status",
                                                    logger=self._logger, config=self._config)

        conn = g._db
        db_name = self._config.get("MySql", "db")

        with conn.cursor() as cursor:
            if id_:
                query = """SELECT Digs.digs_core_number FROM `{}`.`Requests` Requests
                    JOIN `{}`.`Digs` as Digs
                    ON Digs.id = digs_id
                    WHERE Requests.`id` LIKE
                    (SELECT request_id FROM `{}`.`Extracts` WHERE id LIKE {})
                """.format(db_name, db_name, db_name, id_)

                try:
                    cursor.execute(query)
                except Exception:
                    raise ApiSqlException()
                else:
                    columns = [field[0] for field in cursor.description]
                    res = cursor.fetchone()
                    if res:
                        extracts_digs = dict(zip(columns, [res[0]]))

                        if extracts_digs["digs_core_number"] not in user.get("digs").keys():
                            raise ApiUnauthorizedOperationException(
                                title="Cannot modify extract without admin role for facility sequencing this extract",
                                description="Cannot modify extract without admin role for facility sequencing this extract",
                                logger=self._logger, config=self._config)

                        # TODO: validate that the digs for each and every extracts is authorized for the user, not only the one in the id
                        extracts_to_update_status = list(
                            set(map(lambda x: str(x), payload.get("extracts_to_update_status"))))

                        query = """
                              UPDATE `{}`.`Extracts` SET `status`="{}" WHERE `id` in ({});
                        """.format(db_name, payload.get("value"), ",".join(extracts_to_update_status))
                        try:
                            cursor.execute(query)
                            conn.commit()
                        except Exception as e:
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            raise ApiSqlException(title=str(e), description=str(e),
                                                  logger=self._logger, config=self._config, stacktrace=exc_value)
                        else:
                            return True
