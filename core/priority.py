"""Priority Engine - dynamic priority calculation for engineering issues."""

from core.diagnostics import IssueCategory, RootCause


class PriorityEngine:
    """Calculate dynamic priority based on multiple factors."""

    def calculate_priority(
        self,
        impact: str,
        occurrences: int,
        confidence: float,
        category: IssueCategory,
        regression_required: bool
    ) -> int:
        """Calculate priority score from multiple factors.

        Priority = impact_score + frequency_bonus + confidence_bonus + category_weight + regression_bonus
        """

        # Base impact score
        impact_score = self._impact_to_score(impact)

        # Frequency bonus (diminishing returns after 10 occurrences)
        if occurrences <= 10:
            frequency_bonus = occurrences * 10
        else:
            frequency_bonus = 100 + ((occurrences - 10) * 5)
        frequency_bonus = min(frequency_bonus, 200)  # Cap at 200

        # Confidence bonus (higher confidence = higher priority)
        confidence_bonus = int(confidence * 50)

        # Category weight (some categories are more critical)
        category_weight = self._category_to_weight(category)

        # Regression bonus (issues needing regression tests are higher priority)
        regression_bonus = 20 if regression_required else 0

        total = impact_score + frequency_bonus + confidence_bonus + category_weight + regression_bonus
        return total

    def _impact_to_score(self, impact: str) -> int:
        """Convert impact level to score."""
        return {
            "HIGH": 100,
            "MEDIUM": 50,
            "LOW": 10
        }.get(impact, 10)

    def _category_to_weight(self, category: IssueCategory) -> int:
        """Some categories are inherently more critical."""
        critical_categories = {
            IssueCategory.ARCHITECTURE: 30,
            IssueCategory.EXECUTOR: 25,
            IssueCategory.REGRESSION: 25,
            IssueCategory.PLANNER: 20,
            IssueCategory.MEMORY: 15,
            IssueCategory.PERFORMANCE: 10,
            IssueCategory.TOOL: 15,
            IssueCategory.CAPABILITY_GAP: 20,
        }
        return critical_categories.get(category, 5)

    def should_escalate(self, priority: int, occurrences: int) -> bool:
        """Determine if an issue should be escalated for immediate attention."""
        # Escalate if priority is very high
        if priority > 300:
            return True

        # Escalate if occurring very frequently
        if occurrences > 20:
            return True

        return False
