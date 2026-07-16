from app.discovery.snmp.parser import parse_ip_neighbors,parse_ipv4_routes,parse_inet_routes

def test_modern_neighbor_parser_supports_ipv6():
    rows=[{"oid":"iso.3.6.1.2.1.4.35.1.4.7.2.16.32.1.13.184.0.0.0.0.0.0.0.0.0.0.0.66","value":"00:11:22:33:44:55"}]
    assert parse_ip_neighbors(rows)==[{"if_index":7,"ip_address":"2001:db8::42","mac_address":"00:11:22:33:44:55"}]

def test_ipv4_route_parser_groups_columns():
    suffix="10.0.0.0.255.255.255.0.0.192.0.2.1"
    rows=[{"oid":f"iso.3.6.1.2.1.4.24.4.1.1.{suffix}","value":"10.0.0.0"},{"oid":f"iso.3.6.1.2.1.4.24.4.1.2.{suffix}","value":"255.255.255.0"},{"oid":f"iso.3.6.1.2.1.4.24.4.1.4.{suffix}","value":"192.0.2.1"},{"oid":f"iso.3.6.1.2.1.4.24.4.1.5.{suffix}","value":"7"},{"oid":f"iso.3.6.1.2.1.4.24.4.1.7.{suffix}","value":"13"}]
    assert parse_ipv4_routes(rows)[0]|{"metric":None}=={"prefix":"10.0.0.0/24","next_hop":"192.0.2.1","if_index":7,"protocol":"ospf","metric":None}

def test_inet_route_parser_decodes_ipv6_prefix():
    suffix="2.16.32.1.13.184.0.0.0.0.0.0.0.0.0.0.0.0.64"
    rows=[{"oid":f"iso.3.6.1.2.1.4.24.7.1.7.{suffix}","value":"12"}]
    assert parse_inet_routes(rows)[0]["prefix"]=="2001:db8::/64"
