import pytest
from app.discovery.nmap.plugin import build_nmap_args,build_scan_args

def test_udp_profile_is_rate_limited():
    args=build_nmap_args({"profile":"udp"},privileged=True)
    assert "-sU" in args
    assert args[args.index("--max-rate")+1]=="50"

def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError,match="non supporté"):build_nmap_args({"profile":"arbitrary"})

def test_unsafe_rate_is_rejected():
    with pytest.raises(ValueError,match="compris"):build_nmap_args({"profile":"deep","max_rate":5001})

def test_ipv6_target_enables_nmap_ipv6_mode():
    assert build_scan_args("2001:db8::/64",{"profile":"fast"})[0]=="-6"

def test_standard_profile_drops_os_detection_without_root():
    args=build_nmap_args({"profile":"standard"},privileged=False)
    assert "-O" not in args
    assert "--osscan-limit" not in args
    assert "-sV" in args

def test_standard_profile_keeps_os_detection_with_root():
    args=build_nmap_args({"profile":"standard"},privileged=True)
    assert "-O" in args
    assert "--osscan-limit" in args

def test_udp_profile_explains_required_privileges():
    with pytest.raises(ValueError,match="privilèges root"):
        build_nmap_args({"profile":"udp"},privileged=False)
