from enum import Enum


class SubscriptionMode(str, Enum):
    limited_traffic_unlimited_devices = "limited_traffic_unlimited_devices"
    unlimited_traffic_limited_devices = "unlimited_traffic_limited_devices"
    limited_traffic_limited_devices = "limited_traffic_limited_devices"
    unlimited_traffic_unlimited_devices = "unlimited_traffic_unlimited_devices"


DEFAULT_ADMIN_SUBSCRIPTION_MODES = (
    SubscriptionMode.limited_traffic_unlimited_devices,
    SubscriptionMode.unlimited_traffic_limited_devices,
    SubscriptionMode.limited_traffic_limited_devices,
)


class PenaltyAction(str, Enum):
    warn = "warn"
    temporary_disable = "temporary_disable"
    permanent_disable = "permanent_disable"
    delete = "delete"


class PenaltyStatus(str, Enum):
    clear = "clear"
    warning = "warning"
    temporarily_disabled = "temporarily_disabled"
    permanently_disabled = "permanently_disabled"
    deleted = "deleted"
