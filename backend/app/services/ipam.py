import ipaddress

def usable_capacity(prefix:str)->int:
    network=ipaddress.ip_network(prefix,strict=False)
    if network.version==6:return network.num_addresses
    if network.prefixlen>=31:return network.num_addresses
    return network.num_addresses-2
