import pytest
from app.services.vendors import infer_device_type,infer_mobile_identity,is_private_mac,normalize_mac,normalize_vendor,vendor_from_mac

@pytest.mark.parametrize(("raw","expected"),[("Apple, Inc.","Apple"),("Samsung Electronics Co.,Ltd","Samsung"),("Google LLC","Google"),("Xiaomi Communications Co Ltd","Xiaomi"),("Motorola Mobility LLC","Motorola"),("HMD Global Oy","HMD"),("Shenzhen Transsion Holdings","Tecno"),("Cisco Systems","Cisco Systems")])
def test_mobile_vendor_normalization(raw,expected):
    assert normalize_vendor(raw)==expected

def test_google_pixel_identity_from_dns_hostname():
    assert infer_mobile_identity(hostname="Pixel-9-Pro.lan")=={"manufacturer":"Google","device_type":"phone","operating_system":"Android"}

def test_generic_android_is_os_not_vendor():
    assert infer_mobile_identity(operating_system="Android 15")=={"device_type":"phone","operating_system":"Android"}

def test_iphone_is_apple_ios_phone():
    assert infer_mobile_identity(hostname="iPhone.lan",operating_system="Apple iOS 15.7")=={"manufacturer":"Apple","device_type":"phone","operating_system":"Apple iOS"}

def test_phone_mac_formats_are_normalized():
    assert normalize_mac("aa-bb-cc-dd-ee-ff")=="AA:BB:CC:DD:EE:FF"
    assert normalize_mac("aabb.ccdd.eeff")=="AA:BB:CC:DD:EE:FF"
    assert is_private_mac("02:11:22:33:44:55")

def test_offline_oui_lookup_ignores_private_addresses():
    assert vendor_from_mac("00:0C:29:12:34:56")=="VMware"
    assert vendor_from_mac("02:0C:29:12:34:56") is None

def test_device_type_inference_from_network_identity():
    assert infer_device_type(hostname="_gateway",manufacturer="Sagemcom Broadband SAS")=="router"
    assert infer_device_type(hostname="aurel-l5IRH8",operating_system="Windows 11")=="workstation"
    assert infer_device_type(ports={9100})=="printer"
