import xml.etree.ElementTree as ET
import sys

tree = ET.parse('res.xml')
root = tree.getroot()
failures = bool(int(root.attrib.get("failures")))

print("parsing xml. Failed? : ", str(failures))
if failures:
    sys.exit(1)
sys.exit(0)

