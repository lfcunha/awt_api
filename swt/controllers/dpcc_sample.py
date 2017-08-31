from ._controller import ModelControllerFactory as _controller
import requests
from swt.exceptions.api_expections import ApiPreconditionFailedException, ApiException
from uuid import uuid4
import sys


class DpccSample(_controller):
    """Get Information about a Digs facility (capacity, contact, current usage)

    """

    def __init__(self, *args):
        super(DpccSample, self).__init__(*args)

    def usernameToFullName(self, submitter_name):
        user_ = self.user.get_user(submitter_name, swt=False, ldap=True)
        return """{} {}""".format(user_.get("ldap", {}).get("actor_first_name"),
                                  user_.get("ldap", {}).get("actor_last_name"))

    def get_dpcc_samples(self, user, sample_id):
        query = """{}/solr/analytic/select?q=sample_identifier%3A{}&wt=json&indent=true""".format(
            self._config.get("solr", "url"), sample_id)

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        rate, res = None, None
        try:
            res = requests.get(query, headers=headers)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise ApiException(
                description="""Error contacting solr to get information for sample {}""".format(sample_id),
                title="API error", logger=self._logger, config=self._config, stacktrace=exc_value)
        else:
            if res.status_code < 400:
                resp = res.json()
                if resp.get("response", {}).get("numFound") > 0:
                    user_authorized_projects = user.get("ldap", {}).get("projects", {}).keys()
                    resp_ = resp.get("response", {})
                    s = resp_.get("docs")
                    full_name = self.usernameToFullName(s[0].get("submitter_name"))
                    if s[0].get("project_identifier") not in user_authorized_projects:
                        sample = {"sample": [{"submitter_name": full_name,
                                              "project_identifier": s[0].get("project_identifier"),
                                              "sample_identifier": sample_id}]}
                        sample["authorized"] = False
                        sample["new_sample"] = False
                        sample["PI"] = full_name
                        sample["project_identifier"] = s[0].get("project_identifier")
                        sample["status"] = True
                        sample["statusText"] = ""
                        return sample
                    else:
                        unacceptable_submission_types = ["serology", "antibody reagent", "protein reagent",
                                                         "bioproject registration", "sequence"]
                        acceptable_sample_status = ["accepted", "selected for transfer", "exported", "completed"]
                        previously_sequenced = False
                        s_ = [d for d in s if
                              (d.get("sample_status", "") or "").lower() in acceptable_sample_status]
                        has_unacceptable_submission_type = False
                        for d in s_:
                            d["acceptable_submission_type"] = (d.get("submission_type", "") or "").lower() not in unacceptable_submission_types
                            if not d["acceptable_submission_type"]:
                                has_unacceptable_submission_type = True

                        for doc in s_:
                            doc["authorized"] = True
                            doc["new_sample"] = False
                            if doc["submission_type"].lower() == "sequence":
                                previously_sequenced = True
                            doc["submitter_name"] = self.usernameToFullName(doc["submitter_name"])
                        resp_["authorized"] = True
                        resp_["new_sample"] = False
                        s_ = [{"sample_identifier": sample_id, "header": True}] + s_
                        sample = {"sample": s_}
                        sample["has_unacceptable_submission_type"] = has_unacceptable_submission_type
                        sample["authorized"] = True
                        sample["new_sample"] = False
                        sample["display"] = True
                        sample["previously_sequenced"] = previously_sequenced
                        sample["sample_identifier"] = sample_id
                        sample["status"] = True
                        sample["statusText"] = ""
                        return sample
                else:
                    sample = {"sample": [{"sample_identifier": sample_id, "header": True,
                                          "sample_id": str(uuid4()), "new_sample": True},
                                         {"sample_identifier": sample_id,
                                          "sample_id": str(uuid4()), "new_sample": True}]}
                    sample["authorized"] = True
                    sample["new_sample"] = True
                    sample["display"] = True  # flag to toggle the display/hide to samples within a SampleID.
                    sample["status"] = True
                    sample["statusText"] = ""
                    return sample
            else:
                self._logger.error("Error contacting solr to get information for sample {}".format(sample_id))
                raise ApiPreconditionFailedException(title="Error contacting solr", description="Error contacting solr",
                                                     logger=self._logger, config=self._config)
