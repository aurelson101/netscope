from app.workers.tasks import module_targets

def test_snmp_uses_discovered_hosts_for_network():
    assert module_targets("snmp","192.168.1.0/24",{"192.168.1.20","192.168.1.3"})==["192.168.1.3","192.168.1.20"]

def test_snmp_single_host_network_is_supported():
    assert module_targets("snmp","192.168.1.10/32",set())==["192.168.1.10"]

def test_snmp_does_not_walk_a_whole_undiscovered_network():
    assert module_targets("snmp","192.168.1.0/24",set())==[]

def test_nmap_keeps_original_network_target():
    assert module_targets("nmap","192.168.1.0/24",set())==["192.168.1.0/24"]

def test_arp_keeps_ipv6_target_for_ndp_discovery():
    assert module_targets("arp","2001:db8::/64",set())==["2001:db8::/64"]
