from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SiteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class SiteOut(SiteCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class SubnetCreate(BaseModel):
    cidr: str
    name: str
    site_id: str | None = None
    state: str = "discovered"


class SubnetOut(SubnetCreate):
    id: str
    last_scan_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ScanCreate(BaseModel):
    target: str
    profile_id: str
    credential_id: str | None = None
    vrf_id: str | None = None
    probe_id: str | None = None
    confirm_large_network: bool = False
    confirm_public_network: bool = False

class PassiveConnectorCreate(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    kind: str = Field(pattern=r"^(dhcp|arp|dns|wireless|generic)$")
    vrf_id: str | None = None

class PassiveEvent(BaseModel):
    event_id: str = Field(min_length=1,max_length=120)
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = Field(default=None,max_length=255)
    observed_at: datetime | None = None

class PassiveEventBatch(BaseModel):
    events: list[PassiveEvent] = Field(min_length=1,max_length=500)

class ProbeCreate(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    site_id: str | None = None
    vrf_id: str | None = None

class ProbeHeartbeat(BaseModel):
    version: str = Field(max_length=40)
    capabilities: list[str] = Field(min_length=1,max_length=10)

class ProbeFact(BaseModel):
    field: str = Field(min_length=1,max_length=80)
    value: str | int | float | bool | dict | list
    confidence: float = Field(ge=0,le=1)

class ProbeObservation(BaseModel):
    source: str = Field(pattern=r"^(icmp|arp|nmap|dns)$")
    target: str
    raw: dict = Field(default_factory=dict)
    facts: list[ProbeFact] = Field(max_length=1000)

class ProbeTaskResult(BaseModel):
    claim_token: str = Field(min_length=36,max_length=36)
    status: str = Field(pattern=r"^(completed|failed)$")
    error: str | None = Field(default=None,max_length=2000)
    observations: list[ProbeObservation] = Field(default_factory=list,max_length=10000)

class WirelessObservationCreate(BaseModel):
    asset_id: str
    radio_name: str = Field(min_length=1,max_length=120)
    band: str | None = Field(default=None,pattern=r"^(2\.4 GHz|5 GHz|6 GHz)$")
    channel: int | None = Field(default=None,ge=1,le=233)
    channel_width_mhz: int | None = Field(default=None,ge=5,le=320)
    tx_power_dbm: float | None = Field(default=None,ge=-20,le=100)
    utilization: float | None = Field(default=None,ge=0,le=100)
    noise_dbm: float | None = Field(default=None,ge=-150,le=0)
    radio_client_count: int = Field(default=0,ge=0,le=100000)
    ssid: str = Field(min_length=1,max_length=255)
    bssid: str = Field(min_length=12,max_length=32)
    security: str | None = Field(default=None,max_length=40)
    vlan_id: int | None = Field(default=None,ge=1,le=4094)
    hidden: bool = False
    client_count: int = Field(default=0,ge=0,le=100000)

class ScanScheduleCreate(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    target: str
    profile_id: str
    credential_id: str | None = None
    vrf_id: str | None = None
    probe_id: str | None = None
    interval_minutes: int = Field(ge=5,le=525600)
    enabled: bool = True

class ScanScheduleUpdate(BaseModel):
    name: str | None = Field(default=None,min_length=2,max_length=120)
    target: str | None = None
    profile_id: str | None = None
    credential_id: str | None = None
    vrf_id: str | None = None
    probe_id: str | None = None
    interval_minutes: int | None = Field(default=None,ge=5,le=525600)
    enabled: bool | None = None

class UserCreate(BaseModel):
    username: str = Field(min_length=3,max_length=80,pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12,max_length=256)
    role: str = Field(pattern=r"^(admin|operator|viewer)$")

class UserUpdate(BaseModel):
    role: str | None = Field(default=None,pattern=r"^(admin|operator|viewer)$")
    active: bool | None = None
    password: str | None = Field(default=None,min_length=12,max_length=256)

class SnmpTest(BaseModel):
    target: str
    credential_id: str | None = None
    oids: list[str] = Field(default=["1.3.6.1.2.1.1.1.0","1.3.6.1.2.1.1.2.0","1.3.6.1.2.1.1.5.0"],min_length=1,max_length=20)


class ScanOut(BaseModel):
    id: str
    target: str
    profile_id: str
    vrf_id: str | None
    probe_id: str | None
    status: str
    progress: int
    current_module: str | None
    result_count: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    model_config = ConfigDict(from_attributes=True)


class AddressOut(BaseModel):
    address: str
    version: int
    vrf_id: str | None = None
    model_config = ConfigDict(from_attributes=True)


class IdentifierOut(BaseModel):
    kind: str
    value: str
    confidence: float
    model_config = ConfigDict(from_attributes=True)


class ServiceOut(BaseModel):
    protocol: str
    port: int
    name: str | None
    product: str | None
    version: str | None
    model_config = ConfigDict(from_attributes=True)


class AssetOut(BaseModel):
    id: str
    status: str
    hostname: str | None
    manufacturer: str | None
    model: str | None
    device_type: str
    operating_system: str | None
    confidence: float
    first_seen: datetime
    last_seen: datetime
    addresses: list[AddressOut] = []
    identifiers: list[IdentifierOut] = []
    services: list[ServiceOut] = []
    model_config = ConfigDict(from_attributes=True)


class SnmpCredentialCreate(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    username: str = Field(min_length=1,max_length=120)
    security_level: str = "authPriv"
    auth_protocol: str = "SHA"
    auth_password: str | None = Field(default=None,min_length=8)
    privacy_protocol: str = "AES"
    privacy_password: str | None = Field(default=None,min_length=8)
    site_id: str | None = None

class SnmpV2CredentialCreate(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    community: str = Field(min_length=1,max_length=255)
    site_id: str | None = None


class PrefixCreate(BaseModel):
    prefix: str
    name: str = Field(min_length=1,max_length=160)
    status: str = "active"
    role: str | None = None
    vlan_id: str | None = None
    site_id: str | None = None
    vrf_id: str | None = None
    parent_id: str | None = None
    gateway: str | None = None
    dns_servers: list[str] = []
    description: str | None = None


class PrefixUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    role: str | None = None
    gateway: str | None = None
    dns_servers: list[str] | None = None
    description: str | None = None


class MfaCode(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")

class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8,max_length=256)
    new_password: str = Field(min_length=12,max_length=256)

class ReportEmail(BaseModel):
    report_type: str = Field(pattern=r"^(inventory|ipam|scans|vendors|security)$")
    sender: str = Field(min_length=3,max_length=254)
    recipients: list[str] = Field(min_length=1,max_length=20)
    subject: str | None = Field(default=None,max_length=200)
    message: str | None = Field(default=None,max_length=2000)
    format: str = Field(default="pdf",pattern=r"^(csv|pdf)$")

class ReportScheduleCreate(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    report_type: str = Field(pattern=r"^(inventory|ipam|scans|vendors|security)$")
    format: str = Field(default="pdf",pattern=r"^(csv|pdf)$")
    sender: str = Field(min_length=3,max_length=254)
    recipients: list[str] = Field(min_length=1,max_length=20)
    interval_minutes: int = Field(ge=15,le=525600)
    enabled: bool = True

class ReportScheduleUpdate(BaseModel):
    name: str | None = Field(default=None,min_length=2,max_length=120)
    report_type: str | None = Field(default=None,pattern=r"^(inventory|ipam|scans|vendors|security)$")
    format: str | None = Field(default=None,pattern=r"^(csv|pdf)$")
    sender: str | None = Field(default=None,min_length=3,max_length=254)
    recipients: list[str] | None = Field(default=None,min_length=1,max_length=20)
    interval_minutes: int | None = Field(default=None,ge=15,le=525600)
    enabled: bool | None = None

class VrfCreate(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    route_distinguisher: str | None = Field(default=None,max_length=80)
    description: str | None = None

class IpRangeCreate(BaseModel):
    prefix_id: str
    start_address: str
    end_address: str
    role: str = Field(default="dhcp",max_length=40)
    description: str | None = None

class DhcpReservationCreate(BaseModel):
    prefix_id: str
    address: str
    mac_address: str = Field(pattern=r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    hostname: str | None = Field(default=None,max_length=255)
    description: str | None = None

class ConfigurationSnapshotCreate(BaseModel):
    comment: str | None = Field(default=None,max_length=255)


class IpAddressCreate(BaseModel):
    address: str
    prefix_id: str | None = None
    vrf_id: str | None = None
    asset_id: str | None = None
    status: str = "active"
    role: str | None = None
    dns_name: str | None = None
    description: str | None = None


class AssetUpdate(BaseModel):
    hostname: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    serial_number: str | None = None
    role: str | None = None
    platform: str | None = None
    owner: str | None = None
    criticality: str | None = None
    notes: str | None = None
    custom_fields: dict = {}


class TopologyLinkCreate(BaseModel):
    source_asset_id: str
    target_asset_id: str
    source_port: str | None = None
    target_port: str | None = None
    description: str | None = None

class TopologyLinkUpdate(BaseModel):
    source_port: str | None = Field(default=None,max_length=160)
    target_port: str | None = Field(default=None,max_length=160)
    reverse: bool = False


class ManualAssetCreate(BaseModel):
    ip_address: str
    mac_address: str | None = Field(default=None,pattern=r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    hostname: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    device_type: str = "unknown"
    operating_system: str | None = None
    role: str | None = None
    owner: str | None = None
    criticality: str | None = None
    notes: str | None = None


class ArchiveAsset(BaseModel):
    reason: str | None = None


class DnsTest(BaseModel):
    server: str
    ip_address: str

class VlanCreate(BaseModel):
    vlan_id: int = Field(ge=1,le=4094)
    name: str = Field(min_length=1,max_length=120)
    site_id: str | None = None
    prefix_id: str

class DatacenterServiceCreate(BaseModel):
    protocol: str = Field(pattern=r"^(tcp|udp)$")
    port: int = Field(ge=1,le=65535)
    name: str | None = None

class DatacenterDeviceCreate(BaseModel):
    hostname: str = Field(min_length=1,max_length=255)
    ip_address: str
    site_id: str
    vlan_id: str
    description: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    device_type: str = "server"
    operating_system: str | None = None
    services: list[DatacenterServiceCreate] = []
