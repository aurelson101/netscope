import pytest
from app.discovery.nmap.plugin import build_nmap_args

def test_udp_profile_is_rate_limited():
    args=build_nmap_args({"profile":"udp"})
    assert "-sU" in args
    assert args[args.index("--max-rate")+1]=="50"

def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError,match="non supporté"):build_nmap_args({"profile":"arbitrary"})

def test_unsafe_rate_is_rejected():
    with pytest.raises(ValueError,match="compris"):build_nmap_args({"profile":"deep","max_rate":5001})
