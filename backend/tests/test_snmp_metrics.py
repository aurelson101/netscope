from app.discovery.snmp.parser import parse_neighbors,snmp_integer
from app.services.infrastructure import counter_rate

def test_snmp_integer_parses_counters_and_timeticks():
    assert snmp_integer("123456789012") == 123456789012
    assert snmp_integer("(98765) 0:16:27.65") == 98765
    assert snmp_integer("No Such Instance") is None

def test_counter_rate_handles_reset_and_calculates_bits_per_second():
    assert counter_rate(2000,1000,10)==800
    assert counter_rate(10,1000,10) is None

def test_lldp_neighbor_pairs_name_and_port_using_full_index():
    sections={"lldp":[
        {"oid":"iso.0.8802.1.1.2.1.4.1.1.9.12.24.1","value":"switch-edge"},
        {"oid":"iso.0.8802.1.1.2.1.4.1.1.7.12.24.1","value":"Gi1/0/48"},
    ]}
    assert parse_neighbors(sections)==[{"protocol":"lldp","label":"switch-edge","local_if_index":24,"remote_port":"Gi1/0/48"}]

def test_cdp_neighbor_uses_local_interface_index():
    sections={"cdp":[
        {"oid":"SNMPv2-SMI::enterprises.9.9.23.1.2.1.1.6.7.2","value":"router-core"},
        {"oid":"SNMPv2-SMI::enterprises.9.9.23.1.2.1.1.7.7.2","value":"TenGig1/1"},
    ]}
    assert parse_neighbors(sections)[0]["local_if_index"]==7
