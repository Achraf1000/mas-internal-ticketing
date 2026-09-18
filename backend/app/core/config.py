from functools import lru_cache
import json
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    app_name: str = "MAS Ticketing API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    auto_create_tables: bool = True

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    auth_enable_local_fallback: bool = False
    auth_local_allow_temp_password: bool = True

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])

    sqlserver_host: str = "localhost"
    sqlserver_port: int = 1433
    sqlserver_instance: str | None = None
    sqlserver_database: str = "mas_ticketing"
    sqlserver_user: str = "sa"
    sqlserver_password: str = "ChangeMe_123!"
    sqlserver_driver: str = "ODBC Driver 18 for SQL Server"
    sqlserver_trust_server_certificate: bool = True
    sqlserver_encrypt: bool = False
    sqlalchemy_database_uri: str | None = None

    ldap_server_uri: str = "ldap://localhost:389"
    ldap_base_dn: str = "dc=example,dc=local"
    ldap_user_dn_template: str = "mail={email},ou=people,dc=example,dc=local"
    ldap_bind_user: str | None = None
    ldap_bind_password: str | None = None
    ldap_use_ssl: bool = False
    ldap_admin_groups: Annotated[list[str], NoDecode] = Field(default_factory=list)
    ldap_it_groups: Annotated[list[str], NoDecode] = Field(default_factory=list)

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_sender: str = "ticketing@mas.local"

    notification_max_attempts: int = 5
    notification_batch_size: int = 50
    ticket_close_2fa_ttl_minutes: int = 10
    ticket_close_2fa_max_attempts: int = 5
    ticket_close_2fa_debug_return_code: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return ["http://localhost:5173"]
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    pass
            return [origin.strip().strip("'\"") for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return ["http://localhost:5173"]

    @field_validator("ldap_admin_groups", "ldap_it_groups", mode="before")
    @classmethod
    def _parse_group_lists(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(group).strip() for group in parsed if str(group).strip()]
                except json.JSONDecodeError:
                    pass
            return [group.strip().strip("'\"") for group in value.split(",") if group.strip()]
        if isinstance(value, list):
            return [str(group).strip() for group in value if str(group).strip()]
        return []

    @property
    def database_url(self) -> str:
        if self.sqlalchemy_database_uri:
            return self.sqlalchemy_database_uri

        server = self.sqlserver_host
        if self.sqlserver_instance:
            server = f"{self.sqlserver_host}\\{self.sqlserver_instance}"
        else:
            server = f"{self.sqlserver_host},{self.sqlserver_port}"

        trust = "yes" if self.sqlserver_trust_server_certificate else "no"
        encrypt = "yes" if self.sqlserver_encrypt else "no"
        odbc_connect = (
            f"DRIVER={{{self.sqlserver_driver}}};"
            f"SERVER={server};"
            f"DATABASE={self.sqlserver_database};"
            f"UID={self.sqlserver_user};"
            f"PWD={self.sqlserver_password};"
            f"TrustServerCertificate={trust};"
            f"Encrypt={encrypt}"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_connect)}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
