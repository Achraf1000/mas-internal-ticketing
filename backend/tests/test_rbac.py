from app.models.enums import Role
from app.services.rbac import resolve_role_from_ldap_groups


def test_resolve_admin_role(monkeypatch) -> None:
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "ldap_admin_groups", ["cn=admins"])
    monkeypatch.setattr(config_module.settings, "ldap_it_groups", ["cn=it"])

    assert resolve_role_from_ldap_groups(["CN=Admins"]) == Role.ADMIN


def test_resolve_it_role(monkeypatch) -> None:
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "ldap_admin_groups", ["cn=admins"])
    monkeypatch.setattr(config_module.settings, "ldap_it_groups", ["cn=it"])

    assert resolve_role_from_ldap_groups(["CN=IT"]) == Role.IT_AGENT


def test_resolve_default_user_role(monkeypatch) -> None:
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "ldap_admin_groups", ["cn=admins"])
    monkeypatch.setattr(config_module.settings, "ldap_it_groups", ["cn=it"])

    assert resolve_role_from_ldap_groups(["cn=other"]) == Role.USER

