from dataclasses import dataclass
import logging

from ldap3 import ALL, Connection, Server
from ldap3.core.exceptions import LDAPException

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LdapAuthResult:
    is_authenticated: bool
    full_name: str | None = None
    groups: list[str] | None = None
    error: str | None = None


class LDAPService:
    def __init__(self) -> None:
        self.server = Server(
            settings.ldap_server_uri,
            use_ssl=settings.ldap_use_ssl,
            get_info=ALL,
        )

    def authenticate(self, email: str, password: str) -> LdapAuthResult:
        if not password:
            return LdapAuthResult(is_authenticated=False, error="Empty password")

        username = email.split("@")[0]
        user_dn = settings.ldap_user_dn_template.format(email=email, username=username)

        try:
            user_conn = Connection(
                self.server,
                user=user_dn,
                password=password,
                auto_bind=True,
                receive_timeout=6,
            )
        except LDAPException as exc:
            logger.warning("LDAP bind failed for %s: %s", email, exc)
            return LdapAuthResult(is_authenticated=False, error="LDAP authentication failed")

        groups: list[str] = []
        full_name: str | None = None
        try:
            user_conn.search(
                search_base=settings.ldap_base_dn,
                search_filter=f"(mail={email})",
                attributes=["displayName", "cn", "memberOf"],
                size_limit=1,
            )
            if user_conn.entries:
                entry = user_conn.entries[0]
                full_name = str(getattr(entry, "displayName", "") or getattr(entry, "cn", "")).strip() or None
                member_of = getattr(entry, "memberOf", None)
                if member_of:
                    groups = [str(item).strip() for item in member_of if str(item).strip()]
        except LDAPException as exc:
            logger.warning("LDAP group lookup failed for %s: %s", email, exc)
        finally:
            user_conn.unbind()

        return LdapAuthResult(
            is_authenticated=True,
            full_name=full_name,
            groups=groups,
        )

