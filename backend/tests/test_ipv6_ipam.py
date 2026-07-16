from app.services.ipam import usable_capacity

def test_ipv6_capacity_does_not_remove_network_and_broadcast():
    assert usable_capacity("2001:db8::/126")==4

def test_ipv4_point_to_point_capacity_keeps_both_addresses():
    assert usable_capacity("192.0.2.0/31")==2

def test_ipv4_lan_capacity_excludes_network_and_broadcast():
    assert usable_capacity("192.0.2.0/30")==2
