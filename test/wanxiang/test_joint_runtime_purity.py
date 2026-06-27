# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""保证联合分布运行时纯净:不依赖离线工具(tools.synthpop)/xlrd/pandas。

联合分布的 IPF 计算 + .xls 解析全在离线 tools/synthpop,运行时只从存好的
个体池抽样。本测试确保 builder/joint loader 的 import 链不拖入这些重依赖,
保持 Docker 镜像零新依赖。
"""
from __future__ import annotations

import sys


def test_builder_and_joint_import_without_offline_deps():
    # 触发联合分布运行时代码路径的 import
    import wanxiang.personas.builder  # noqa: F401
    import wanxiang.datasources.joint  # noqa: F401
    import wanxiang.datasources.distribution  # noqa: F401
    # 这些是离线/构建期依赖,运行时不应被加载
    for forbidden in ("tools.synthpop", "xlrd", "pandas"):
        assert forbidden not in sys.modules, \
            f"运行时不应加载 {forbidden}(应只在离线 tools/ 用)"


def test_joint_sampling_works_with_stdlib_only():
    """联合抽样只用 numpy+stdlib(bisect/random)。"""
    from wanxiang.datasources.joint import load_joint_from_dict
    from wanxiang.personas.builder import PersonaBuilder
    raw = {
        "joint": {
            "version": 1, "method": "ipf", "level": "test",
            "dimensions": [
                {"key": {"zh": "性别", "en": "gender"},
                 "categories": [{"zh": "男", "en": "male"},
                                {"zh": "女", "en": "female"}],
                 "coupling": "joint"},
            ],
            "households": [
                {"weight": 3.0, "members": [[0]]},
                {"weight": 1.0, "members": [[1]]},
            ],
            "provenance": {},
        }
    }
    jv = load_joint_from_dict(raw)
    assert jv is not None and jv.household_count() == 2
    dist = {"demographic": [], "personality": [], "media": [], "__joint__": jv}
    ps = PersonaBuilder().sample(dist, n=20, seed=1, locale="zh")
    assert len(ps) == 20
    assert all(p.household_id is not None for p in ps)
    # 男(weight3)应明显多于女(weight1)
    males = sum(1 for p in ps if p.demographic.get("性别") == "男")
    assert males > 10
