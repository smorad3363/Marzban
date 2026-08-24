from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class BillingMode(str, Enum):
    LEGACY_COMPAT = "LEGACY_COMPAT"
    SEAT_CREDIT = "SEAT_CREDIT"
    USED_TRAFFIC = "USED_TRAFFIC"
    ALLOCATED_TRAFFIC = "ALLOCATED_TRAFFIC"
    USER_CREDIT = "USER_CREDIT"


class BillingModeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def billing_mode(settings: Any) -> BillingMode:
    value = getattr(settings, "billing_mode", None) or BillingMode.LEGACY_COMPAT.value
    try:
        return BillingMode(value)
    except ValueError as exc:
        raise BillingModeError("invalid_billing_mode", f"Unsupported billing mode: {value}") from exc


def finite_seat_cost(concurrent_user_limit: int | None) -> int:
    if concurrent_user_limit is None:
        raise BillingModeError(
            "seat_plan_requires_finite_devices",
            "SEAT_CREDIT requires an explicit finite positive device/concurrency count",
        )
    value = int(concurrent_user_limit)
    if value <= 0:
        raise BillingModeError(
            "seat_plan_requires_finite_devices",
            "SEAT_CREDIT rejects zero, unlimited, or non-positive device/concurrency counts",
        )
    return value


@dataclass(frozen=True)
class BillingStrategy:
    mode: BillingMode

    def validate_plan(self, concurrent_user_limit: int | None) -> None:
        return None

    def create_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        return 0

    def update_capacity_charge(
        self,
        old_concurrent_user_limit: int | None,
        new_concurrent_user_limit: int | None,
    ) -> int:
        return 0

    def delete_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        return 0

    def allocated_charge(
        self,
        old_data_limit: int | None,
        new_data_limit: int | None,
        *,
        renewal: bool,
    ) -> int:
        return 0


class LegacyCompatStrategy(BillingStrategy):
    def create_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        if concurrent_user_limit is None:
            return 1
        value = int(concurrent_user_limit)
        if value < 1:
            raise BillingModeError(
                "invalid_user_limit",
                "Concurrent user limit must be a positive integer",
            )
        return value

    def update_capacity_charge(
        self,
        old_concurrent_user_limit: int | None,
        new_concurrent_user_limit: int | None,
    ) -> int:
        return self.create_capacity_charge(new_concurrent_user_limit) - self.create_capacity_charge(
            old_concurrent_user_limit
        )

    def delete_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        return -self.create_capacity_charge(concurrent_user_limit)

    def allocated_charge(
        self,
        old_data_limit: int | None,
        new_data_limit: int | None,
        *,
        renewal: bool,
    ) -> int:
        return max(int(new_data_limit or 0) - int(old_data_limit or 0), 0)


class SeatCreditStrategy(BillingStrategy):
    def validate_plan(self, concurrent_user_limit: int | None) -> None:
        finite_seat_cost(concurrent_user_limit)

    def create_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        return finite_seat_cost(concurrent_user_limit)

    def update_capacity_charge(
        self,
        old_concurrent_user_limit: int | None,
        new_concurrent_user_limit: int | None,
    ) -> int:
        old_cost = finite_seat_cost(old_concurrent_user_limit)
        new_cost = finite_seat_cost(new_concurrent_user_limit)
        return max(new_cost - old_cost, 0)


class UserCreditStrategy(BillingStrategy):
    """Unlimited traffic where each owned account costs one user credit."""

    def create_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        # max_users is the canonical counter for this mode. Device capacity is
        # intentionally untouched so device count never changes account cost.
        return 0

    def update_capacity_charge(
        self,
        old_concurrent_user_limit: int | None,
        new_concurrent_user_limit: int | None,
    ) -> int:
        return 0

    def delete_capacity_charge(self, concurrent_user_limit: int | None) -> int:
        return 0


class AllocatedTrafficStrategy(BillingStrategy):
    def allocated_charge(
        self,
        old_data_limit: int | None,
        new_data_limit: int | None,
        *,
        renewal: bool,
    ) -> int:
        new_value = int(new_data_limit or 0)
        if renewal:
            return new_value
        return max(new_value - int(old_data_limit or 0), 0)


STRATEGIES: dict[BillingMode, BillingStrategy] = {
    BillingMode.LEGACY_COMPAT: LegacyCompatStrategy(BillingMode.LEGACY_COMPAT),
    BillingMode.SEAT_CREDIT: SeatCreditStrategy(BillingMode.SEAT_CREDIT),
    BillingMode.USED_TRAFFIC: BillingStrategy(BillingMode.USED_TRAFFIC),
    BillingMode.ALLOCATED_TRAFFIC: AllocatedTrafficStrategy(BillingMode.ALLOCATED_TRAFFIC),
    BillingMode.USER_CREDIT: UserCreditStrategy(BillingMode.USER_CREDIT),
}


def strategy_for(settings: Any) -> BillingStrategy:
    return STRATEGIES[billing_mode(settings)]
