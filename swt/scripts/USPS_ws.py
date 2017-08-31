import urllib
import requests
from xml.etree import ElementTree


def usps_shipping(dest_zip=None, origin_zip=None):
    """ Calculate rate
    :param: originZip (int): origin zipcode
    :param: destZip (int): destination zipcode

    :raises: Exception if usps returns error in the calculation, like due to zipcode error
    :returns: float | None   the shipping rate, or None if there's problems reaching the usps api.
    """

    if not all([origin_zip, dest_zip]):  # pragma: no cover
        raise Exception("please provide both origin and destination zipcode")

    #devurl = "http://testing.shippingapis.com/ShippingAPITest.dll";
    liveurl = "http://production.shippingapis.com/ShippingAPI.dll";

    service = "RateV4"
    user_id = ""

    xml = """<RateV4Request USERID="{}">
                <Revision>2</Revision>
                <Package ID="1ST">
                    <Service >PRIORITY CPP</Service>
                    <ZipOrigination>{}</ZipOrigination>
                    <ZipDestination>{}</ZipDestination>
                    <Pounds>0</Pounds>
                    <Ounces>3.5</Ounces>
                    <Container/>
                    <Size>REGULAR</Size>
                    <Machinable>true</Machinable>
                </Package>
            </RateV4Request> """.format(user_id, origin_zip, dest_zip)

    r_xml = urllib.parse.quote(xml)
    r_xml.replace("/", "%2f")

    #url = liveurl + "?API=" + service + "&xml=" + r_xml
    url = """{}?API={}&xml={}""".format(liveurl, service, r_xml)
    headers = {'Accept': 'application/xml', 'Content-Type': 'application/xml'}

    rate, res = None, None
    try:
        res = requests.get(url, headers=headers)
    except Exception:
        return None  #  problem reaching the usps api. return None. FSE will ignore calculation
    else:
        if res:
            if res.status_code < 400:
                try:
                    tree = ElementTree.fromstring(res.content)
                except Exception:  # pragma: no cover
                    return None  # there was some error with usps' response. Can't parse xml

                if len(tree[0]) < 2:  # if can't calculate shipping due to zipcode error, element at tree[0][0] is <Element 'Error' at 0x10c2db810>
                    raise Exception("can't calculate shipping rate. Check that the zipcode is valid")

                rate = float(tree.findall("./Package/Postage/Rate")[0].text)
            else:  # pragma: no cover
                return None  # zipcode errors are returned in the xml. if status code >= 400, it's an error on their side. skip, after 3 tries, rate will be returned as None and FSE will skip
    return rate
