# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""calibration: 校准与分布保真度评估（spec §M5 护城河，轻量版）。"""
from wanxiang.calibration.fidelity import (FidelityReport,
                                            calibrate,
                                            calibrate_categorical,
                                            calibrate_numeric)

__all__ = ["FidelityReport", "calibrate",
           "calibrate_categorical", "calibrate_numeric"]
