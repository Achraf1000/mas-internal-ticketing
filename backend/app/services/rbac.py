from app.core.config import settings
from app.models.enums import Role


def resolve_role_from_ldap_groups(groups: list[str] | None) -> Role:
    normalized = {group.lower() for group in (groups or [])}
    admin_groups = {group.lower() for group in settings.ldap_admin_groups}
    it_groups = {group.lower() for group in settings.ldap_it_groups}
    if normalized.intersection(admin_groups):
        return Role.ADMIN
    if normalized.intersection(it_groups):
        return Role.IT_AGENT
    return Role.USER

