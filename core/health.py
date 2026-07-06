"""Health monitor - objective system health evaluation."""

import psutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HealthLevel(Enum):
    """System health level."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthStatus:
    """Objective system health status."""
    level: HealthLevel
    reasons: list[str]

    cpu_percent: float
    ram_percent: float
    disk_percent: Optional[float] = None
    swap_percent: Optional[float] = None
    battery_percent: Optional[int] = None
    battery_charging: Optional[bool] = None
    internet_reachable: bool = True

    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.level == HealthLevel.HEALTHY

    @property
    def is_warning(self) -> bool:
        """Check if system has warnings."""
        return self.level == HealthLevel.WARNING

    @property
    def is_critical(self) -> bool:
        """Check if system is in critical state."""
        return self.level == HealthLevel.CRITICAL


def evaluate_health(internet_reachable: bool = True) -> HealthStatus:
    """Evaluate objective system health.

    Returns:
        HealthStatus with level (Healthy/Warning/Critical) and objective reasons
    """
    reasons = []
    level = HealthLevel.HEALTHY

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.5)

    # RAM usage
    ram = psutil.virtual_memory()
    ram_percent = ram.percent

    # Disk usage for root
    disk_percent = None
    try:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
    except Exception:
        pass

    # Swap usage
    swap_percent = None
    try:
        swap = psutil.swap_memory()
        swap_percent = swap.percent
    except Exception:
        pass

    # Battery status
    battery_percent = None
    battery_charging = None
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = int(battery.percent)
            battery_charging = battery.power_plugged
    except Exception:
        pass

    # Evaluate critical conditions
    if ram_percent >= 95:
        level = HealthLevel.CRITICAL
        reasons.append(f"RAM usage critical: {ram_percent:.1f}%")

    if disk_percent and disk_percent >= 95:
        level = HealthLevel.CRITICAL
        reasons.append(f"Disk usage critical: {disk_percent:.1f}%")

    if battery_percent and battery_percent <= 10 and not battery_charging:
        level = HealthLevel.CRITICAL
        reasons.append(f"Battery critical: {battery_percent}% (not charging)")

    if not internet_reachable:
        if level == HealthLevel.HEALTHY:
            level = HealthLevel.WARNING
        reasons.append("No internet connectivity")

    # Evaluate warning conditions (only if not already critical)
    if level != HealthLevel.CRITICAL:
        if ram_percent >= 85:
            level = HealthLevel.WARNING
            reasons.append(f"RAM usage high: {ram_percent:.1f}%")

        if cpu_percent >= 90:
            level = HealthLevel.WARNING
            reasons.append(f"CPU usage high: {cpu_percent:.1f}%")

        if disk_percent and disk_percent >= 85:
            level = HealthLevel.WARNING
            reasons.append(f"Disk usage high: {disk_percent:.1f}%")

        if swap_percent and swap_percent >= 50:
            level = HealthLevel.WARNING
            reasons.append(f"Swap usage high: {swap_percent:.1f}%")

        if battery_percent and battery_percent <= 20 and not battery_charging:
            level = HealthLevel.WARNING
            reasons.append(f"Battery low: {battery_percent}% (not charging)")

    return HealthStatus(
        level=level,
        reasons=reasons,
        cpu_percent=cpu_percent,
        ram_percent=ram_percent,
        disk_percent=disk_percent,
        swap_percent=swap_percent,
        battery_percent=battery_percent,
        battery_charging=battery_charging,
        internet_reachable=internet_reachable,
    )
