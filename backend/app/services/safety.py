import ipaddress
from fastapi import HTTPException
from app.core.config import settings


def validate_target(target: str, confirm_large: bool = False, confirm_public: bool = False) -> str:
    try:
        network = ipaddress.ip_network(target, strict=False)
    except ValueError as exc:
        raise HTTPException(422, "Cible IP/CIDR invalide") from exc
    if network.prefixlen == 0 or network.is_loopback or network.is_multicast or network.is_unspecified:
        raise HTTPException(422, "Plage interdite")
    if network.num_addresses > settings.max_scan_hosts and not confirm_large:
        raise HTTPException(422, "Confirmation requise pour ce réseau de grande taille")
    if not network.is_private and not confirm_public:
        raise HTTPException(422, "Les réseaux publics exigent une autorisation explicite")
    return str(network)
