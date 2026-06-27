# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""离线合成人口工具(build-time only,不被 wanxiang/ API import)。

依赖 pandas + xlrd(仅离线/构建期),运行时镜像不含这些。
负责:读七普 .xls 交叉表 → IPF 计算联合分布 → 产出合成个体池 JSON。
"""
