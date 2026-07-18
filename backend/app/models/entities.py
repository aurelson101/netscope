import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Role(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class AssetStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    unknown = "unknown"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Subnet(Base):
    __tablename__ = "subnets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cidr: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(24), default="discovered")
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id"))
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScanProfile(Base):
    __tablename__ = "scan_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    modules: Mapped[list] = mapped_column(JSON, default=list)
    options: Mapped[dict] = mapped_column(JSON, default=dict)


class ScanJob(Base):
    __tablename__ = "scan_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target: Mapped[str] = mapped_column(String(64))
    profile_id: Mapped[str] = mapped_column(ForeignKey("scan_profiles.id"))
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credentials.id"))
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    probe_id: Mapped[str | None] = mapped_column(ForeignKey("probes.id"), index=True)
    probe_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    probe_claim_token: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_module: Mapped[str | None] = mapped_column(String(30))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class ScanSchedule(Base):
    __tablename__ = "scan_schedules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    target: Mapped[str] = mapped_column(String(64))
    profile_id: Mapped[str] = mapped_column(ForeignKey("scan_profiles.id"))
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credentials.id"))
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    probe_id: Mapped[str | None] = mapped_column(ForeignKey("probes.id"), index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.unknown)
    hostname: Mapped[str | None] = mapped_column(String(255), index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(160))
    model: Mapped[str | None] = mapped_column(String(160))
    device_type: Mapped[str] = mapped_column(String(80), default="unknown")
    operating_system: Mapped[str | None] = mapped_column(String(160))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id"))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    addresses: Mapped[list["AssetAddress"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    identifiers: Mapped[list["AssetIdentifier"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    services: Mapped[list["AssetService"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class AssetAddress(Base):
    __tablename__ = "asset_addresses"
    __table_args__ = (
        Index("uq_asset_addresses_global", "asset_id", "address", unique=True, sqlite_where=text("vrf_id IS NULL"), postgresql_where=text("vrf_id IS NULL")),
        Index("uq_asset_addresses_vrf", "asset_id", "address", "vrf_id", unique=True, sqlite_where=text("vrf_id IS NOT NULL"), postgresql_where=text("vrf_id IS NOT NULL")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    address: Mapped[str] = mapped_column(String(64), index=True)
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=4)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NetworkIdentityBinding(Base):
    __tablename__ = "network_identity_bindings"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), index=True)
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    mac_address: Mapped[str | None] = mapped_column(String(32), index=True)
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    source: Mapped[str] = mapped_column(String(50))
    scan_id: Mapped[str | None] = mapped_column(ForeignKey("scan_jobs.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class AssetIdentifier(Base):
    __tablename__ = "asset_identifiers"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    kind: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(String(255), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1)


class AssetService(Base):
    __tablename__ = "asset_services"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    protocol: Mapped[str] = mapped_column(String(8))
    port: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(80))
    product: Mapped[str | None] = mapped_column(String(160))
    version: Mapped[str | None] = mapped_column(String(80))


class RawObservation(Base):
    __tablename__ = "raw_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id: Mapped[str | None] = mapped_column(ForeignKey("scan_jobs.id"))
    source: Mapped[str] = mapped_column(String(50))
    target: Mapped[str] = mapped_column(String(255))
    raw_data: Mapped[dict] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PassiveConnector(Base):
    __tablename__ = "passive_connectors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PassiveEventReceipt(Base):
    __tablename__ = "passive_event_receipts"
    __table_args__ = (UniqueConstraint("connector_id","event_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    connector_id: Mapped[str] = mapped_column(ForeignKey("passive_connectors.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(120))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Probe(Base):
    __tablename__ = "probes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id"), index=True)
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    capabilities: Mapped[list] = mapped_column(JSON,default=list)
    reachable_networks: Mapped[list] = mapped_column(JSON,default=list)
    version: Mapped[str | None] = mapped_column(String(40))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    observation_id: Mapped[str] = mapped_column(ForeignKey("raw_observations.id"))
    source: Mapped[str] = mapped_column(String(50))
    field: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AssetHistory(Base):
    __tablename__ = "asset_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('info','warning','critical')",name="ck_alerts_severity"),
        CheckConstraint("status IN ('open','acknowledged','resolved')",name="ck_alerts_status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fingerprint: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning", index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Credential(Base):
    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(30), default="snmpv3")
    encrypted_secret: Mapped[str] = mapped_column(Text)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id"))
    description: Mapped[str | None] = mapped_column(String(255))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now,onupdate=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DeviceConfiguration(Base):
    __tablename__ = "device_configurations"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"),index=True)
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credentials.id"))
    platform: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20),default="queued",index=True)
    encrypted_content: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(64))
    byte_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceConfigurationRestore(Base):
    __tablename__ = "device_configuration_restores"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    configuration_id: Mapped[str] = mapped_column(ForeignKey("device_configurations.id"),index=True)
    pre_backup_id: Mapped[str | None] = mapped_column(ForeignKey("device_configurations.id"))
    status: Mapped[str] = mapped_column(String(20),default="queued",index=True)
    error: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Vlan(Base):
    __tablename__ = "vlans"
    __table_args__ = (UniqueConstraint("site_id", "vlan_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vlan_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id"))
    source: Mapped[str] = mapped_column(String(40), default="snmp")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NetworkDevice(Base):
    __tablename__ = "network_devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), unique=True)
    management_ip: Mapped[str | None] = mapped_column(String(64))
    sys_name: Mapped[str | None] = mapped_column(String(255))
    sys_descr: Mapped[str | None] = mapped_column(Text)
    sys_object_id: Mapped[str | None] = mapped_column(String(255))
    uptime_ticks: Mapped[int | None] = mapped_column(Integer)
    last_polled: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SwitchPort(Base):
    __tablename__ = "switch_ports"
    __table_args__ = (UniqueConstraint("network_device_id", "if_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    network_device_id: Mapped[str] = mapped_column(ForeignKey("network_devices.id"))
    if_index: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(String(255))
    mac_address: Mapped[str | None] = mapped_column(String(32))
    admin_status: Mapped[str | None] = mapped_column(String(20))
    oper_status: Mapped[str | None] = mapped_column(String(20))
    vlan_id: Mapped[int | None] = mapped_column(Integer)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InterfaceMetric(Base):
    __tablename__ = "interface_metrics"
    __table_args__ = (Index("ix_interface_metrics_port_time","switch_port_id","collected_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    switch_port_id: Mapped[str] = mapped_column(ForeignKey("switch_ports.id"), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)
    speed_bps: Mapped[int | None] = mapped_column(BigInteger)
    in_octets: Mapped[int | None] = mapped_column(BigInteger)
    out_octets: Mapped[int | None] = mapped_column(BigInteger)
    in_errors: Mapped[int | None] = mapped_column(BigInteger)
    out_errors: Mapped[int | None] = mapped_column(BigInteger)
    in_bps: Mapped[float | None] = mapped_column(Float)
    out_bps: Mapped[float | None] = mapped_column(Float)
    in_utilization: Mapped[float | None] = mapped_column(Float)
    out_utilization: Mapped[float | None] = mapped_column(Float)


class PortMacEntry(Base):
    __tablename__ = "port_mac_entries"
    __table_args__ = (UniqueConstraint("switch_port_id", "mac_address", "vlan_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    switch_port_id: Mapped[str] = mapped_column(ForeignKey("switch_ports.id"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    mac_address: Mapped[str] = mapped_column(String(32), index=True)
    vlan_id: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30), default="snmp_fdb")
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArpEntry(Base):
    __tablename__ = "arp_entries"
    __table_args__ = (UniqueConstraint("network_device_id", "ip_address", "mac_address"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    network_device_id: Mapped[str] = mapped_column(ForeignKey("network_devices.id"))
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    mac_address: Mapped[str] = mapped_column(String(32), index=True)
    if_index: Mapped[int | None] = mapped_column(Integer)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RouteEntry(Base):
    __tablename__ = "route_entries"
    __table_args__ = (UniqueConstraint("network_device_id","vrf_id","prefix","next_hop","protocol",name="uq_route_entry_identity"),)
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    network_device_id: Mapped[str] = mapped_column(ForeignKey("network_devices.id"),index=True)
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"),index=True)
    prefix: Mapped[str] = mapped_column(String(64),index=True)
    next_hop: Mapped[str | None] = mapped_column(String(64))
    if_index: Mapped[int | None] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(30),default="unknown")
    metric: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean,default=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)


class WirelessRadio(Base):
    __tablename__ = "wireless_radios"
    __table_args__ = (UniqueConstraint("asset_id","radio_name",name="uq_wireless_radio_asset_name"),)
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"),index=True)
    radio_name: Mapped[str] = mapped_column(String(120))
    band: Mapped[str | None] = mapped_column(String(20))
    channel: Mapped[int | None] = mapped_column(Integer)
    channel_width_mhz: Mapped[int | None] = mapped_column(Integer)
    tx_power_dbm: Mapped[float | None] = mapped_column(Float)
    utilization: Mapped[float | None] = mapped_column(Float)
    noise_dbm: Mapped[float | None] = mapped_column(Float)
    client_count: Mapped[int] = mapped_column(Integer,default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)


class WirelessNetwork(Base):
    __tablename__ = "wireless_networks"
    __table_args__ = (UniqueConstraint("bssid",name="uq_wireless_network_bssid"),)
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    radio_id: Mapped[str] = mapped_column(ForeignKey("wireless_radios.id"),index=True)
    ssid: Mapped[str] = mapped_column(String(255),index=True)
    bssid: Mapped[str] = mapped_column(String(32),index=True)
    security: Mapped[str | None] = mapped_column(String(40))
    vlan_id: Mapped[int | None] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean,default=False)
    client_count: Mapped[int] = mapped_column(Integer,default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)


class TopologyNode(Base):
    __tablename__ = "topology_nodes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), unique=True)
    label: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(60), default="unknown")


class TopologyLink(Base):
    __tablename__ = "topology_links"
    __table_args__ = (UniqueConstraint("source_node_id","target_node_id","source","source_port","target_port",name="uq_topology_link_ports"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_node_id: Mapped[str] = mapped_column(ForeignKey("topology_nodes.id"))
    target_node_id: Mapped[str] = mapped_column(ForeignKey("topology_nodes.id"))
    source_port: Mapped[str | None] = mapped_column(String(160))
    target_port: Mapped[str | None] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DeviceRole(Base):
    __tablename__ = "device_roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str] = mapped_column(String(12), default="3b82f6")
    description: Mapped[str | None] = mapped_column(Text)


class IpamPrefix(Base):
    __tablename__ = "ipam_prefixes"
    __table_args__ = (
        Index("uq_ipam_prefixes_global", "prefix", unique=True, sqlite_where=text("vrf_id IS NULL"), postgresql_where=text("vrf_id IS NULL")),
        Index("uq_ipam_prefixes_vrf", "prefix", "vrf_id", unique=True, sqlite_where=text("vrf_id IS NOT NULL"), postgresql_where=text("vrf_id IS NOT NULL")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prefix: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="active")
    role: Mapped[str | None] = mapped_column(String(80))
    vlan_id: Mapped[str | None] = mapped_column(ForeignKey("vlans.id"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id"))
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("ipam_prefixes.id"))
    gateway: Mapped[str | None] = mapped_column(String(64))
    dns_servers: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IpamAddress(Base):
    __tablename__ = "ipam_addresses"
    __table_args__ = (
        Index("uq_ipam_addresses_global", "address", unique=True, sqlite_where=text("vrf_id IS NULL"), postgresql_where=text("vrf_id IS NULL")),
        Index("uq_ipam_addresses_vrf", "address", "vrf_id", unique=True, sqlite_where=text("vrf_id IS NOT NULL"), postgresql_where=text("vrf_id IS NOT NULL")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    address: Mapped[str] = mapped_column(String(64), index=True)
    prefix_id: Mapped[str | None] = mapped_column(ForeignKey("ipam_prefixes.id"))
    vrf_id: Mapped[str | None] = mapped_column(ForeignKey("vrfs.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    status: Mapped[str] = mapped_column(String(30), default="active")
    role: Mapped[str | None] = mapped_column(String(80))
    dns_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), default="manual")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Vrf(Base):
    __tablename__ = "vrfs"
    __table_args__ = (UniqueConstraint("name", "route_distinguisher"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), index=True)
    route_distinguisher: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IpRange(Base):
    __tablename__ = "ip_ranges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prefix_id: Mapped[str] = mapped_column(ForeignKey("ipam_prefixes.id"), index=True)
    start_address: Mapped[str] = mapped_column(String(64))
    end_address: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(40), default="dhcp")
    description: Mapped[str | None] = mapped_column(Text)


class DhcpReservation(Base):
    __tablename__ = "dhcp_reservations"
    __table_args__ = (UniqueConstraint("prefix_id", "address"), UniqueConstraint("prefix_id", "mac_address"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prefix_id: Mapped[str] = mapped_column(ForeignKey("ipam_prefixes.id"), index=True)
    address: Mapped[str] = mapped_column(String(64), index=True)
    mac_address: Mapped[str] = mapped_column(String(32), index=True)
    hostname: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReportSchedule(Base):
    __tablename__ = "report_schedules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    report_type: Mapped[str] = mapped_column(String(40))
    format: Mapped[str] = mapped_column(String(10), default="pdf")
    sender: Mapped[str] = mapped_column(String(254))
    recipients: Mapped[list] = mapped_column(JSON, default=list)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=10080)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConfigurationVersion(Base):
    __tablename__ = "configuration_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version: Mapped[int] = mapped_column(Integer, unique=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    comment: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AssetMetadata(Base):
    __tablename__ = "asset_metadata"
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    serial_number: Mapped[str | None] = mapped_column(String(160))
    role: Mapped[str | None] = mapped_column(String(100))
    platform: Mapped[str | None] = mapped_column(String(120))
    owner: Mapped[str | None] = mapped_column(String(160))
    criticality: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class UserMfa(Base):
    __tablename__ = "user_mfa"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    encrypted_secret: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssetArchive(Base):
    __tablename__ = "asset_archives"
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    archived_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
