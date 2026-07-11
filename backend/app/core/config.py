from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NetScope"
    database_url: str = "sqlite+aiosqlite:///./netscope.db"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "development-only-change-me-32-bytes-minimum"
    master_encryption_key: str = "development-master-key-change-me-32-bytes"
    admin_username: str = "admin"
    admin_password: str = "ChangeMeNow!"
    access_token_minutes: int = 120
    cors_origins: str = "http://localhost:8080,http://localhost:5173"
    max_scan_hosts: int = 4096
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout: int = 15
    smtp_senders: str = ""
    snmp_default_version: str = ""
    snmpv3_username: str = ""
    snmpv3_security_level: str = "authPriv"
    snmpv3_auth_protocol: str = "SHA"
    snmpv3_auth_password: str = ""
    snmpv3_privacy_protocol: str = "AES"
    snmpv3_privacy_password: str = ""
    snmpv2_community: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def smtp_sender_list(self)->list[str]:
        return [x.strip() for x in self.smtp_senders.split(",") if x.strip()]

    @property
    def snmp_default_credential(self)->dict|None:
        version=self.snmp_default_version.strip().lower()
        if version in ("2","2c","v2c") and self.snmpv2_community:return {"version":"2c","community":self.snmpv2_community}
        if version in ("3","v3") and self.snmpv3_username:return {"version":"3","username":self.snmpv3_username,"security_level":self.snmpv3_security_level,"auth_protocol":self.snmpv3_auth_protocol,"auth_password":self.snmpv3_auth_password or None,"privacy_protocol":self.snmpv3_privacy_protocol,"privacy_password":self.snmpv3_privacy_password or None}
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
