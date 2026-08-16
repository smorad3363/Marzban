import os
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import select, text

from app import xray
from app.db.base import Base
from app.models.node import NodeStatus
from app.models.proxy import (
    ProxyHostALPN,
    ProxyHostFingerprint,
    ProxyHostSecurity,
    ProxyTypes,
)
from app.models.user import ReminderType, UserDataLimitResetStrategy, UserStatus


def utc_now_naive() -> datetime:
    """Return UTC in the naive format used by existing database timestamps."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String(34), unique=True, index=True)
    hashed_password = Column(String(128))
    users = relationship("User", back_populates="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sudo = Column(Boolean, default=False)
    password_reset_at = Column(DateTime, nullable=True)
    telegram_id = Column(BigInteger, nullable=True, default=None)
    discord_webhook = Column(String(1024), nullable=True, default=None)
    users_usage = Column(BigInteger, nullable=False, default=0)
    usage_logs = relationship("AdminUsageLogs", back_populates="admin")


class AdminUsageLogs(Base):
    __tablename__ = "admin_usage_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    admin = relationship("Admin", back_populates="usage_logs")
    used_traffic_at_reset = Column(BigInteger, nullable=False)
    reset_at = Column(DateTime, default=datetime.utcnow)


class AdminAuditLog(Base):
    """Append-only record of sensitive administrative activity."""

    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_admin_audit_logs_admin_created", "admin_id", "created_at"),
        Index("ix_admin_audit_logs_action_created", "action", "created_at"),
        Index(
            "ix_admin_audit_logs_target",
            "target_type",
            "target_id",
        ),
        Index(
            "ix_admin_audit_logs_target_name_created",
            "target_name",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_username = Column(String(34), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(128), nullable=True)
    target_name = Column(String(256), nullable=True)
    description = Column(Text, nullable=False)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    status = Column(String(16), nullable=False, default="success")
    created_at = Column(
        DateTime,
        nullable=False,
        default=utc_now_naive,
        index=True,
    )


class MarzhelpMetadata(Base):
    """Compatibility metadata owned and migrated by Marzban."""

    __tablename__ = "marzhelp_metadata"

    key = Column(String(64), primary_key=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class MarzhelpAdminSettings(Base):
    """Canonical Marzhelp policy and admin-accounting settings."""

    __tablename__ = "marzhelp_admin_settings"

    admin_id = Column(Integer, ForeignKey("admins.id"), primary_key=True)
    total_traffic = Column(BigInteger, nullable=True)
    used_traffic = Column(BigInteger, nullable=False, default=0)
    expiry_date = Column(Date, nullable=True)
    status = Column(JSON, nullable=True)
    # Remaining successful create operations. NULL means unrestricted.
    user_limit = Column(BigInteger, nullable=True)
    # Maximum owned user accounts. NULL means unrestricted.
    max_users = Column(BigInteger, nullable=True)
    user_count_used = Column(BigInteger, nullable=False, default=0)
    # Legacy weighted concurrent-device capacity is preserved independently.
    device_capacity_limit = Column(BigInteger, nullable=True)
    capacity_used = Column(BigInteger, nullable=False, default=0)
    provisioning_volume_limit = Column(BigInteger, nullable=True)
    provisioning_volume_used = Column(BigInteger, nullable=False, default=0)
    renewal_limit = Column(BigInteger, nullable=True)
    renewals_used = Column(BigInteger, nullable=False, default=0)
    all_inbounds = Column(Boolean, nullable=False, default=True)
    all_user_limits = Column(Boolean, nullable=False, default=True)
    max_user_duration_days = Column(Integer, nullable=True)
    hashed_password_before = Column(String(255), nullable=True)
    last_expiry_notification = Column(DateTime, nullable=True)
    last_traffic_notification = Column(Integer, nullable=True)
    last_traffic_notify = Column(Integer, nullable=True)
    calculate_volume = Column(String(50), nullable=False, default="used_traffic")
    prevent_user_creation = Column(Boolean, nullable=False, default=False)
    prevent_user_deletion = Column(Boolean, nullable=False, default=False)
    prevent_user_reset = Column(Boolean, nullable=False, default=False)
    prevent_revoke_subscription = Column(Boolean, nullable=False, default=False)
    prevent_unlimited_traffic = Column(Boolean, nullable=False, default=False)
    # Full client addresses are sensitive. Non-sudo admins receive masked
    # addresses unless this capability is explicitly granted by sudo.
    view_full_client_ip = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    inbound_permissions = relationship(
        "MarzhelpAdminInboundPermission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user_limit_permissions = relationship(
        "MarzhelpAdminUserLimitPermission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subscription_mode_permissions = relationship(
        "MarzhelpAdminSubscriptionModePermission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def allowed_inbounds(self):
        return sorted(item.inbound_tag for item in self.inbound_permissions)

    @property
    def allowed_user_limits(self):
        return sorted(item.concurrent_user_limit for item in self.user_limit_permissions)

    @property
    def allowed_subscription_modes(self):
        return sorted(item.mode for item in self.subscription_mode_permissions)


class MarzhelpAdminInboundPermission(Base):
    __tablename__ = "marzhelp_admin_allowed_inbounds"

    admin_id = Column(
        Integer,
        ForeignKey("marzhelp_admin_settings.admin_id", ondelete="CASCADE"),
        primary_key=True,
    )
    inbound_tag = Column(String(256), primary_key=True)


class MarzhelpAdminUserLimitPermission(Base):
    __tablename__ = "marzhelp_admin_allowed_user_limits"

    admin_id = Column(
        Integer,
        ForeignKey("marzhelp_admin_settings.admin_id", ondelete="CASCADE"),
        primary_key=True,
    )
    concurrent_user_limit = Column(Integer, primary_key=True)


class MarzhelpAdminSubscriptionModePermission(Base):
    __tablename__ = "marzhelp_admin_allowed_subscription_modes"

    admin_id = Column(
        Integer,
        ForeignKey("marzhelp_admin_settings.admin_id", ondelete="CASCADE"),
        primary_key=True,
    )
    mode = Column(String(48), primary_key=True)


class DeviceLimitSettings(Base):
    """Singleton runtime policy for native device/IP-limit enforcement."""

    __tablename__ = "device_limit_settings"

    id = Column(Integer, primary_key=True, autoincrement=False, default=1)
    enabled = Column(Boolean, nullable=False, default=False)
    # Kept for input/backward compatibility only. Runtime behavior uses the
    # independent capability flags below.
    enforcement_mode = Column(String(24), nullable=False, default="hybrid")
    device_slots_enabled = Column(Boolean, nullable=False, default=True)
    ip_detection_enabled = Column(Boolean, nullable=False, default=True)
    client_fingerprint_enabled = Column(Boolean, nullable=False, default=False)
    check_interval_seconds = Column(Integer, nullable=False, default=60)
    active_window_seconds = Column(Integer, nullable=False, default=300)
    hit_threshold = Column(Integer, nullable=False, default=3)
    min_successful_connections = Column(Integer, nullable=False, default=3)
    handoff_grace_seconds = Column(Integer, nullable=False, default=90)
    warning_auto_delete_seconds = Column(Integer, nullable=False, default=86400)
    strike_reset_seconds = Column(Integer, nullable=False, default=2592000)
    full_ip_retention_days = Column(Integer, nullable=False, default=7)
    incident_retention_days = Column(Integer, nullable=False, default=90)
    audit_retention_days = Column(Integer, nullable=False, default=180)
    auto_delete_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )


class DeviceLimitPenaltyStage(Base):
    __tablename__ = "device_limit_penalty_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    violation_count = Column(Integer, nullable=False, unique=True)
    action = Column(String(32), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)


class DeviceSlot(Base):
    """One independently revocable credential bundle owned by a user."""

    __tablename__ = "device_slots"
    __table_args__ = (
        UniqueConstraint("user_id", "slot_index", name="uq_device_slots_user_index"),
        Index("ix_device_slots_user_enabled", "user_id", "enabled"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    slot_index = Column(Integer, nullable=False)
    label = Column(String(64), nullable=True)
    credentials = Column(JSON, nullable=False)
    token_version = Column(String(36), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    last_seen_at = Column(DateTime, nullable=True)
    last_ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    user = relationship("User", back_populates="device_slots")
    client_observations = relationship(
        "DeviceClientObservation",
        back_populates="slot",
        lazy="selectin",
    )


class DeviceClientObservation(Base):
    """Aggregated, bounded subscription-client observation per slot/user."""

    __tablename__ = "device_client_observations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "slot_key",
            "normalized_identity",
            name="uq_device_client_observation_identity",
        ),
        Index(
            "ix_device_client_observation_user_slot_seen",
            "user_id",
            "slot_key",
            "last_seen_at",
        ),
        Index(
            "ix_device_client_observation_user_seen",
            "user_id",
            "last_seen_at",
        ),
        Index("ix_device_client_observation_slot", "slot_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Integer, ForeignKey("device_slots.id", ondelete="SET NULL"), nullable=True)
    # 0 is the honest user-level fallback for legacy subscription tokens.
    slot_key = Column(Integer, nullable=False, default=0)
    normalized_identity = Column(String(64), nullable=False)
    client_name = Column(String(64), nullable=False, default="Unknown")
    client_version = Column(String(64), nullable=True)
    platform = Column(String(64), nullable=True)
    os_token = Column(String(128), nullable=True)
    network_stack = Column(String(128), nullable=True)
    raw_user_agent = Column(String(512), nullable=False)
    first_seen_at = Column(DateTime, nullable=False, default=utc_now_naive)
    last_seen_at = Column(DateTime, nullable=False, default=utc_now_naive)
    seen_count = Column(BigInteger, nullable=False, default=1)

    slot = relationship("DeviceSlot", back_populates="client_observations")
    user = relationship("User", back_populates="device_client_observations")


class DeviceLimitUserState(Base):
    __tablename__ = "device_limit_user_states"
    __table_args__ = (
        Index("ix_device_limit_state_penalty_until", "penalty_status", "blocked_until"),
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    violation_count = Column(Integer, nullable=False, default=0)
    current_stage = Column(Integer, nullable=False, default=0)
    penalty_status = Column(String(32), nullable=False, default="clear")
    blocked_until = Column(DateTime, nullable=True)
    status_before_penalty = Column(String(24), nullable=True)
    last_violation_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    active_ip_count = Column(Integer, nullable=False, default=0)
    last_reason = Column(Text, nullable=True)
    pending_handoff_started_at = Column(DateTime, nullable=True)
    pending_ip_addresses = Column(JSON, nullable=True)
    pending_source_nodes = Column(JSON, nullable=True)
    pending_risk_score = Column(Integer, nullable=True)
    pending_last_fresh_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    user = relationship("User", back_populates="device_limit_state")


class DeviceLimitIncident(Base):
    __tablename__ = "device_limit_incidents"
    __table_args__ = (
        Index("ix_device_limit_incidents_user_created", "user_id", "created_at"),
        Index("ix_device_limit_incidents_admin_created", "admin_id", "created_at"),
        Index("ix_device_limit_incidents_created", "created_at"),
        Index(
            "ix_device_limit_incidents_warning_expiry",
            "event_state",
            "resolved_at",
            "expires_at",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_id = Column(Integer, nullable=True)
    username = Column(String(34), nullable=False)
    stage = Column(Integer, nullable=False)
    action = Column(String(32), nullable=False)
    configured_limit = Column(Integer, nullable=False)
    observed_count = Column(Integer, nullable=False)
    ip_addresses = Column(JSON, nullable=True)
    source_nodes = Column(JSON, nullable=True)
    event_state = Column(String(32), nullable=False, default="confirmed_violation")
    risk_score = Column(Integer, nullable=True)
    signal_summary = Column(JSON, nullable=True)
    reason = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)


class MarzhelpUserState(Base):
    __tablename__ = "marzhelp_user_states"

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(50), nullable=True)
    lang = Column(String(10), nullable=True)
    state = Column(String(50), nullable=True)
    admin_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    data = Column(Text, nullable=True)
    message_id = Column(Integer, nullable=True)
    template_index = Column(Integer, nullable=False, default=0)


class MarzhelpUserTemporary(Base):
    __tablename__ = "marzhelp_user_temporaries"

    user_id = Column(BigInteger, primary_key=True)
    user_key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=True)


class MarzhelpAdminUsage(Base):
    __tablename__ = "marzhelp_admin_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    used_traffic_gb = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class MarzhelpLimit(Base):
    __tablename__ = "marzhelp_limits"
    __table_args__ = (UniqueConstraint("type", "admin_id", "inbound_tag", name="uq_marzhelp_limit"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(16), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    inbound_tag = Column(String(255), nullable=False)


class MarzhelpRuntimeSetting(Base):
    __tablename__ = "marzhelp_runtime_settings"

    setting_name = Column(String(64), primary_key=True)
    setting_value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarzhelpDeletedUser(Base):
    __tablename__ = "marzhelp_deleted_users"

    user_id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, nullable=False, index=True)
    username = Column(String(34), nullable=True)
    used_traffic_total = Column(BigInteger, nullable=False, default=0)
    allocated_traffic = Column(BigInteger, nullable=True)
    refunded_traffic = Column(BigInteger, nullable=False, default=0)
    deleted_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class MarzhelpAccountingTransaction(Base):
    __tablename__ = "marzhelp_accounting_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_key = Column(String(128), nullable=False, unique=True)
    operation_type = Column(String(32), nullable=False)
    admin_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(34), nullable=True)
    traffic_delta = Column(BigInteger, nullable=False, default=0)
    allowance_delta = Column(Integer, nullable=False, default=0)
    volume_delta = Column(BigInteger, nullable=False, default=0)
    renewal_delta = Column(Integer, nullable=False, default=0)
    result = Column(String(16), nullable=False, default="consumed")
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(34, collation='NOCASE'), unique=True, index=True)
    proxies = relationship("Proxy", back_populates="user", cascade="all, delete-orphan")
    device_slots = relationship("DeviceSlot", back_populates="user", cascade="all, delete-orphan")
    device_client_observations = relationship(
        "DeviceClientObservation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    device_limit_state = relationship(
        "DeviceLimitUserState",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.active)
    used_traffic = Column(BigInteger, default=0)
    node_usages = relationship("NodeUserUsage", back_populates="user", cascade="all, delete-orphan")
    notification_reminders = relationship("NotificationReminder", back_populates="user", cascade="all, delete-orphan")
    data_limit = Column(BigInteger, nullable=True)
    # NULL keeps the historical unlimited-device behavior.
    concurrent_user_limit = Column(Integer, nullable=True)
    data_limit_reset_strategy = Column(
        Enum(UserDataLimitResetStrategy),
        nullable=False,
        default=UserDataLimitResetStrategy.no_reset,
    )
    usage_logs = relationship("UserUsageResetLogs", back_populates="user")  # maybe rename it to reset_usage_logs?
    expire = Column(Integer, nullable=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), index=True)
    admin = relationship("Admin", back_populates="users")
    sub_revoked_at = Column(DateTime, nullable=True, default=None)
    sub_updated_at = Column(DateTime, nullable=True, default=None)
    sub_last_user_agent = Column(String(512), nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String(500), nullable=True, default=None)
    online_at = Column(DateTime, nullable=True, default=None)
    on_hold_expire_duration = Column(BigInteger, nullable=True, default=None)
    on_hold_timeout = Column(DateTime, nullable=True, default=None)

    # * Positive values: User will be deleted after the value of this field in days automatically.
    # * Negative values: User won't be deleted automatically at all.
    # * NULL: Uses global settings.
    auto_delete_in_days = Column(Integer, nullable=True, default=None)

    edit_at = Column(DateTime, nullable=True, default=None)
    last_status_change = Column(DateTime, default=datetime.utcnow, nullable=True)

    next_plan = relationship(
        "NextPlan",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def reseted_usage(self) -> int:
        return int(sum([log.used_traffic_at_reset for log in self.usage_logs]))

    @reseted_usage.expression
    def reseted_usage(cls):
        return (
            select(func.sum(UserUsageResetLogs.used_traffic_at_reset)).
            where(UserUsageResetLogs.user_id == cls.id).
            label('reseted_usage')
        )

    @property
    def lifetime_used_traffic(self) -> int:
        return int(
            sum([log.used_traffic_at_reset for log in self.usage_logs])
            + self.used_traffic
        )

    @property
    def last_traffic_reset_time(self):
        return self.usage_logs[-1].reset_at if self.usage_logs else self.created_at

    @property
    def reset_history(self):
        return sorted(
            self.usage_logs,
            key=lambda log: log.reset_at or datetime.min,
            reverse=True,
        )

    @property
    def excluded_inbounds(self):
        _ = {}
        for proxy in self.proxies:
            _[proxy.type] = [i.tag for i in proxy.excluded_inbounds]
        return _

    @property
    def inbounds(self):
        _ = {}
        for proxy in self.proxies:
            _[proxy.type] = []
            excluded_tags = [i.tag for i in proxy.excluded_inbounds]
            for inbound in xray.config.inbounds_by_protocol.get(proxy.type, []):
                if inbound["tag"] not in excluded_tags:
                    _[proxy.type].append(inbound["tag"])

        return _


excluded_inbounds_association = Table(
    "exclude_inbounds_association",
    Base.metadata,
    Column("proxy_id", ForeignKey("proxies.id")),
    Column("inbound_tag", ForeignKey("inbounds.tag")),
)

template_inbounds_association = Table(
    "template_inbounds_association",
    Base.metadata,
    Column("user_template_id", ForeignKey("user_templates.id")),
    Column("inbound_tag", ForeignKey("inbounds.tag")),
)


class NextPlan(Base):
    __tablename__ = 'next_plans'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    data_limit = Column(BigInteger, nullable=False)
    expire = Column(Integer, nullable=True)
    add_remaining_traffic = Column(Boolean, nullable=False, default=False, server_default='0')
    fire_on_either = Column(Boolean, nullable=False, default=True, server_default='0')

    user = relationship("User", back_populates="next_plan")


class UserTemplate(Base):
    __tablename__ = "user_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    data_limit = Column(BigInteger, default=0)
    expire_duration = Column(BigInteger, default=0)  # in seconds
    username_prefix = Column(String(20), nullable=True)
    username_suffix = Column(String(20), nullable=True)

    inbounds = relationship(
        "ProxyInbound", secondary=template_inbounds_association
    )


class UserUsageResetLogs(Base):
    __tablename__ = "user_usage_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="usage_logs")
    used_traffic_at_reset = Column(BigInteger, nullable=False)
    reset_at = Column(DateTime, default=datetime.utcnow)


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="proxies")
    type = Column(Enum(ProxyTypes), nullable=False)
    settings = Column(JSON, nullable=False)
    excluded_inbounds = relationship(
        "ProxyInbound", secondary=excluded_inbounds_association
    )


class ProxyInbound(Base):
    __tablename__ = "inbounds"

    id = Column(Integer, primary_key=True)
    tag = Column(String(256), unique=True, nullable=False, index=True)
    hosts = relationship(
        "ProxyHost", back_populates="inbound", cascade="all, delete-orphan"
    )


class ProxyHost(Base):
    __tablename__ = "hosts"
    # __table_args__ = (
    #     UniqueConstraint('inbound_tag', 'remark'),
    # )

    id = Column(Integer, primary_key=True)
    remark = Column(String(256), unique=False, nullable=False)
    address = Column(String(256), unique=False, nullable=False)
    port = Column(Integer, nullable=True)
    path = Column(String(256), unique=False, nullable=True)
    sni = Column(String(1000), unique=False, nullable=True)
    host = Column(String(1000), unique=False, nullable=True)
    security = Column(
        Enum(ProxyHostSecurity),
        unique=False,
        nullable=False,
        default=ProxyHostSecurity.inbound_default,
    )
    alpn = Column(
        Enum(ProxyHostALPN),
        unique=False,
        nullable=False,
        default=ProxyHostSecurity.none,
        server_default=ProxyHostSecurity.none.name
    )
    fingerprint = Column(
        Enum(ProxyHostFingerprint),
        unique=False,
        nullable=False,
        default=ProxyHostSecurity.none,
        server_default=ProxyHostSecurity.none.name
    )

    inbound_tag = Column(String(256), ForeignKey("inbounds.tag"), nullable=False)
    inbound = relationship("ProxyInbound", back_populates="hosts")
    allowinsecure = Column(Boolean, nullable=True)
    is_disabled = Column(Boolean, nullable=True, default=False)
    mux_enable = Column(Boolean, nullable=False, default=False, server_default='0')
    fragment_setting = Column(String(100), nullable=True)
    noise_setting = Column(String(2000), nullable=True)
    random_user_agent = Column(Boolean, nullable=False, default=False, server_default='0')
    use_sni_as_host = Column(Boolean, nullable=False, default=False, server_default="0")


class System(Base):
    __tablename__ = "system"

    id = Column(Integer, primary_key=True)
    uplink = Column(BigInteger, default=0)
    downlink = Column(BigInteger, default=0)


class JWT(Base):
    __tablename__ = "jwt"

    id = Column(Integer, primary_key=True)
    secret_key = Column(
        String(64), nullable=False, default=lambda: os.urandom(32).hex()
    )


class TLS(Base):
    __tablename__ = "tls"

    id = Column(Integer, primary_key=True)
    key = Column(String(4096), nullable=False)
    certificate = Column(String(2048), nullable=False)


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    name = Column(String(256, collation='NOCASE'), unique=True)
    address = Column(String(256), unique=False, nullable=False)
    port = Column(Integer, unique=False, nullable=False)
    api_port = Column(Integer, unique=False, nullable=False)
    xray_version = Column(String(32), nullable=True)
    status = Column(Enum(NodeStatus), nullable=False, default=NodeStatus.connecting)
    last_status_change = Column(DateTime, default=datetime.utcnow)
    message = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    uplink = Column(BigInteger, default=0)
    downlink = Column(BigInteger, default=0)
    user_usages = relationship("NodeUserUsage", back_populates="node", cascade="all, delete-orphan")
    usages = relationship("NodeUsage", back_populates="node", cascade="all, delete-orphan")
    usage_coefficient = Column(Float, nullable=False, server_default=text("1.0"), default=1)
    watchdog_enabled = Column(Boolean, nullable=False, server_default=text("1"), default=True)


class NodeWatchdogSettings(Base):
    __tablename__ = "node_watchdog_settings"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=False)
    telegram_bot_token = Column(String(256), nullable=True)
    telegram_chat_id = Column(String(64), nullable=True)
    check_interval = Column(Integer, nullable=False, default=15)
    backoff_cap = Column(Integer, nullable=False, default=600)
    remind_every = Column(Integer, nullable=False, default=1800)


class NodeUserUsage(Base):
    __tablename__ = "node_user_usages"
    __table_args__ = (
        UniqueConstraint('created_at', 'user_id', 'node_id'),
    )

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, unique=False, nullable=False)  # one hour per record
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="node_usages")
    node_id = Column(Integer, ForeignKey("nodes.id"))
    node = relationship("Node", back_populates="user_usages")
    used_traffic = Column(BigInteger, default=0)


class NodeUsage(Base):
    __tablename__ = "node_usages"
    __table_args__ = (
        UniqueConstraint('created_at', 'node_id'),
    )

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, unique=False, nullable=False)  # one hour per record
    node_id = Column(Integer, ForeignKey("nodes.id"))
    node = relationship("Node", back_populates="usages")
    uplink = Column(BigInteger, default=0)
    downlink = Column(BigInteger, default=0)


class NotificationReminder(Base):
    __tablename__ = "notification_reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="notification_reminders")
    type = Column(Enum(ReminderType), nullable=False)
    threshold = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
