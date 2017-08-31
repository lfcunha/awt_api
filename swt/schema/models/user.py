import pymysql
import requests


class UserLdap(object):
    ldap_url = "http://www.niaidceirs.org/dpcc/api/actors/"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class UserSwt(object):
    """
        CREATE TABLE `DPCC_SWT_DEV`.`Users` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `username` VARCHAR(45) NULL,
          `name` VARCHAR(45) NULL,
          `institution` VARCHAR(128) NULL,
          `street_address` VARCHAR(128) NULL,
          `city` VARCHAR(45) NULL,
          `state_province` VARCHAR(24) NULL,
          `zipcode` SMALLINT(2) NULL,
          `country` VARCHAR(16) NULL,
          `daytime_phone` VARCHAR(16) NULL,
          `email` VARCHAR(32) NULL,
          PRIMARY KEY (`id`),
          UNIQUE INDEX `username_UNIQUE` (`username` ASC),
          UNIQUE INDEX `email_UNIQUE` (`email` ASC));
    """

    id = None
    username = None
    name = None
    institution = None
    street_address = None
    city = None
    state_province = None
    zipcode = None
    country = None
    daytime_phone = None
    email = None

    """
    @property
    def id(self):
        return self._id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._username = name

    @property
    def institution(self):
        return self._institution

    @institution.setter
    def institution(self, institution):
        self._institution = institution

    @property
    def street_address(self):
        return self._street_address

    @street_address.setter
    def street_address(self, street_address):
        self._street_address = street_address

    @property
    def city(self):
        return self._city

    @city.setter
    def city(self, city):
        self._city = city

    @property
    def state_province(self):
        return self._state_province

    @state_province.setter
    def state_province(self, state_province):
        self._state_province = state_province

    @property
    def zipcode(self):
        return self._zipcode

    @zipcode.setter
    def zipcode(self, zipcode):
        self._zipcode = zipcode

    @property
    def country(self):
        return self._country

    @country.setter
    def country(self, country):
        self._country = country

    @property
    def daytime_phone(self):
        return self._daytime_phone

    @daytime_phone.setter
    def daytime_phone(self, daytime_phone):
        self._daytime_phone = daytime_phone

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        self._email = email
    """


class User(object):
    def __init__(self, username):
        self._username
        self.user = dict(UserLdap.user(username), **UserSwt.user(username))


if __name__ == "__main__":  # pragma: no cover
    pass