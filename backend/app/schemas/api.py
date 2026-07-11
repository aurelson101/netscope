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
    confirm_large_network: bool = False
    confirm_public_network: bool = False


class ScanOut(BaseModel):
    id: str
    target: str
    profile_id: str
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    model_config = ConfigDict(from_attributes=True)


class AddressOut(BaseModel):
    address: str
    version: int
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


class IpAddressCreate(BaseModel):
    address: str
    prefix_id: str | None = None
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
