from pathlib import Path
from app.discovery.nmap.parser import parse_nmap_xml


def test_nmap_xml_parser():
    results=parse_nmap_xml((Path(__file__).parent/"fixtures/nmap.xml").read_text())
    assert results[0].target=="10.0.0.5"
    facts={x["field"]:x["value"] for x in results[0].facts if x["field"]!="service"}
    assert facts["mac"]=="AA:BB:CC:DD:EE:FF"
    assert facts["operating_system"]=="Cisco IOS XE"
    assert results[0].raw["services"][0]["port"]==22
