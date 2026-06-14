# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""reasoning: 因果归因 + 反事实推演（spec §M6 收官）。"""
from wanxiang.reasoning.causal import (CausalReport, Factor,
                                         FactorContribution,
                                         analyze_factor_contributions)
from wanxiang.reasoning.counterfactual import (Alternative, AlternativeOutcome,
                                                 CounterfactualReport,
                                                 compare_alternatives)

__all__ = ["Factor", "FactorContribution", "CausalReport",
           "analyze_factor_contributions",
           "Alternative", "AlternativeOutcome", "CounterfactualReport",
           "compare_alternatives"]
