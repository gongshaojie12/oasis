# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""datasources: 分布数据接入（spec §M1 数据接入轻量版）。"""
from wanxiang.datasources.distribution import (load_distribution,
                                               load_distribution_from_dict,
                                               validate_distribution)

__all__ = ["load_distribution", "load_distribution_from_dict",
           "validate_distribution"]
