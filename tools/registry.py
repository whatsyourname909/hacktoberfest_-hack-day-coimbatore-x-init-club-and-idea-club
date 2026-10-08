"""The only deterministic analyses available to planned tests."""

from analysis.comparisons import (breakdown_by_dimension, compare_periods,
                                  contribution_to_change, mix_analysis)
from analysis.data_quality import data_quality_check
from analysis.trends import trend_analysis

ANALYSIS_TOOLS = {
    "compare_periods": compare_periods,
    "breakdown": breakdown_by_dimension,
    "contribution": contribution_to_change,
    "mix": mix_analysis,
    "trend": trend_analysis,
    "data_quality": data_quality_check,
}
