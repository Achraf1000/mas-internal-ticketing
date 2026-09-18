"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-04 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


role_enum = sa.Enum("USER", "IT_AGENT", "ADMIN", name="role")
ticket_status_enum = sa.Enum("NEW", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "CLOSED", name="ticketstatus")
ticket_priority_enum = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="ticketpriority")
ticket_category_enum = sa.Enum("REQUEST", "INCIDENT", "ANOMALY", "VALIDATION", name="ticketcategory")
notification_status_enum = sa.Enum("PENDING", "RETRY", "SENT", "FAILED", name="notificationstatus")


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
        sa.UniqueConstraint("name", name=op.f("uq_departments_name")),
    )
    op.create_index(op.f("ix_departments_code"), "departments", ["code"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("is_department_head", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("ldap_groups", sa.UnicodeText(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_users_department_id_departments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_id", name=op.f("uq_refresh_tokens_token_id")),
    )
    op.create_index(op.f("ix_refresh_tokens_token_id"), "refresh_tokens", ["token_id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "sla_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("priority", ticket_priority_enum, nullable=False),
        sa.Column("first_response_minutes", sa.Integer(), nullable=False),
        sa.Column("resolution_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sla_policies")),
        sa.UniqueConstraint("priority", name=op.f("uq_sla_policies_priority")),
    )
    op.create_index(op.f("ix_sla_policies_priority"), "sla_policies", ["priority"], unique=False)

    op.create_table(
        "tickets",
        sa.Column("id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("ticket_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.UnicodeText(), nullable=False),
        sa.Column("category", ticket_category_enum, nullable=False),
        sa.Column("priority", ticket_priority_enum, nullable=False),
        sa.Column("status", ticket_status_enum, nullable=False),
        sa.Column("emitter_department_id", sa.Integer(), nullable=False),
        sa.Column("target_department_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("assignee_id", mssql.UNIQUEIDENTIFIER(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_tickets_assignee_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
            name=op.f("fk_tickets_creator_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["emitter_department_id"],
            ["departments.id"],
            name=op.f("fk_tickets_emitter_department_id_departments"),
        ),
        sa.ForeignKeyConstraint(
            ["target_department_id"],
            ["departments.id"],
            name=op.f("fk_tickets_target_department_id_departments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tickets")),
        sa.UniqueConstraint("ticket_code", name=op.f("uq_tickets_ticket_code")),
    )
    op.create_index(op.f("ix_tickets_ticket_code"), "tickets", ["ticket_code"], unique=False)
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)
    op.create_index(op.f("ix_tickets_priority"), "tickets", ["priority"], unique=False)
    op.create_index(op.f("ix_tickets_emitter_department_id"), "tickets", ["emitter_department_id"], unique=False)
    op.create_index(op.f("ix_tickets_target_department_id"), "tickets", ["target_department_id"], unique=False)
    op.create_index(op.f("ix_tickets_creator_id"), "tickets", ["creator_id"], unique=False)
    op.create_index(op.f("ix_tickets_assignee_id"), "tickets", ["assignee_id"], unique=False)
    op.create_index(
        "ix_tickets_filter_core",
        "tickets",
        ["status", "priority", "target_department_id", "assignee_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("author_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("body", sa.UnicodeText(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_ticket_comments_author_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_ticket_comments_ticket_id_tickets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_comments")),
    )
    op.create_index(op.f("ix_ticket_comments_ticket_id"), "ticket_comments", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_ticket_comments_author_id"), "ticket_comments", ["author_id"], unique=False)
    op.create_index(op.f("ix_ticket_comments_created_at"), "ticket_comments", ["created_at"], unique=False)

    op.create_table(
        "ticket_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_ticket_attachments_ticket_id_tickets"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_ticket_attachments_uploaded_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_attachments")),
    )
    op.create_index(op.f("ix_ticket_attachments_ticket_id"), "ticket_attachments", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_ticket_attachments_uploaded_at"), "ticket_attachments", ["uploaded_at"], unique=False)

    op.create_table(
        "ticket_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("from_status", ticket_status_enum, nullable=True),
        sa.Column("to_status", ticket_status_enum, nullable=False),
        sa.Column("changed_by", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("reason", sa.UnicodeText(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_ticket_status_history_ticket_id_tickets"),
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name=op.f("fk_ticket_status_history_changed_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_status_history")),
    )
    op.create_index(op.f("ix_ticket_status_history_ticket_id"), "ticket_status_history", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_ticket_status_history_to_status"), "ticket_status_history", ["to_status"], unique=False)
    op.create_index(op.f("ix_ticket_status_history_changed_at"), "ticket_status_history", ["changed_at"], unique=False)

    op.create_table(
        "sla_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", mssql.UNIQUEIDENTIFIER(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_sla_events_ticket_id_tickets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sla_events")),
    )
    op.create_index(op.f("ix_sla_events_ticket_id"), "sla_events", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_sla_events_event_type"), "sla_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_sla_events_deadline_at"), "sla_events", ["deadline_at"], unique=False)
    op.create_index(op.f("ix_sla_events_status"), "sla_events", ["status"], unique=False)
    op.create_index(op.f("ix_sla_events_created_at"), "sla_events", ["created_at"], unique=False)

    op.create_table(
        "notification_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.UnicodeText(), nullable=False),
        sa.Column("status", notification_status_enum, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("last_error", sa.UnicodeText(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_queue")),
    )
    op.create_index(op.f("ix_notification_queue_event_type"), "notification_queue", ["event_type"], unique=False)
    op.create_index(op.f("ix_notification_queue_recipient_email"), "notification_queue", ["recipient_email"], unique=False)
    op.create_index(op.f("ix_notification_queue_status"), "notification_queue", ["status"], unique=False)
    op.create_index(op.f("ix_notification_queue_next_attempt_at"), "notification_queue", ["next_attempt_at"], unique=False)
    op.create_index(op.f("ix_notification_queue_created_at"), "notification_queue", ["created_at"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", mssql.UNIQUEIDENTIFIER(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("before_json", sa.UnicodeText(), nullable=True),
        sa.Column("after_json", sa.UnicodeText(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_notification_queue_created_at"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_next_attempt_at"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_status"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_recipient_email"), table_name="notification_queue")
    op.drop_index(op.f("ix_notification_queue_event_type"), table_name="notification_queue")
    op.drop_table("notification_queue")

    op.drop_index(op.f("ix_sla_events_created_at"), table_name="sla_events")
    op.drop_index(op.f("ix_sla_events_status"), table_name="sla_events")
    op.drop_index(op.f("ix_sla_events_deadline_at"), table_name="sla_events")
    op.drop_index(op.f("ix_sla_events_event_type"), table_name="sla_events")
    op.drop_index(op.f("ix_sla_events_ticket_id"), table_name="sla_events")
    op.drop_table("sla_events")

    op.drop_index(op.f("ix_ticket_status_history_changed_at"), table_name="ticket_status_history")
    op.drop_index(op.f("ix_ticket_status_history_to_status"), table_name="ticket_status_history")
    op.drop_index(op.f("ix_ticket_status_history_ticket_id"), table_name="ticket_status_history")
    op.drop_table("ticket_status_history")

    op.drop_index(op.f("ix_ticket_attachments_uploaded_at"), table_name="ticket_attachments")
    op.drop_index(op.f("ix_ticket_attachments_ticket_id"), table_name="ticket_attachments")
    op.drop_table("ticket_attachments")

    op.drop_index(op.f("ix_ticket_comments_created_at"), table_name="ticket_comments")
    op.drop_index(op.f("ix_ticket_comments_author_id"), table_name="ticket_comments")
    op.drop_index(op.f("ix_ticket_comments_ticket_id"), table_name="ticket_comments")
    op.drop_table("ticket_comments")

    op.drop_index("ix_tickets_filter_core", table_name="tickets")
    op.drop_index(op.f("ix_tickets_assignee_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_creator_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_target_department_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_emitter_department_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_priority"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_ticket_code"), table_name="tickets")
    op.drop_table("tickets")

    op.drop_index(op.f("ix_sla_policies_priority"), table_name="sla_policies")
    op.drop_table("sla_policies")

    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_token_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_departments_code"), table_name="departments")
    op.drop_table("departments")

    notification_status_enum.drop(op.get_bind(), checkfirst=False)
    ticket_category_enum.drop(op.get_bind(), checkfirst=False)
    ticket_priority_enum.drop(op.get_bind(), checkfirst=False)
    ticket_status_enum.drop(op.get_bind(), checkfirst=False)
    role_enum.drop(op.get_bind(), checkfirst=False)

