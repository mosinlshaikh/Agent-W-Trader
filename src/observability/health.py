"""System health aggregation for operational readiness decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: HealthStatus
    detail: str


@dataclass(frozen=True)
class SystemHealth:
    status: HealthStatus
    components: tuple[ComponentHealth, ...]


class HealthService:
    def __init__(self) -> None:
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}

    def register(self, name: str, check: Callable[[], ComponentHealth]) -> None:
        if not name.strip():
            raise ValueError("health-check name cannot be blank")
        self._checks[name] = check

    def evaluate(self) -> SystemHealth:
        components: list[ComponentHealth] = []
        for name, check in self._checks.items():
            try:
                result = check()
                if result.name != name:
                    result = ComponentHealth(name=name, status=result.status, detail=result.detail)
            except Exception as exc:
                result = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    detail=f"health check failed: {exc}",
                )
            components.append(result)

        statuses = {item.status for item in components}
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        return SystemHealth(status=overall, components=tuple(components))
