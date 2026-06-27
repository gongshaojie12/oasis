# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""合成人口的规范类目词表(离线工具用;运行时副本在 wanxiang/datasources/categories.py)。

统一各表的年龄段、性别、学历、婚姻、职业、省份类目 + 中英对照。
不同源表口径要归一到这里(如 B0403 用 16-19,B0503 用 15-19 → 统一)。
"""
from __future__ import annotations

# 统一年龄段(15+,因婚姻/就业表都是 15 或 16 岁起;15-19 含 16-19)
AGE_BANDS = [
    ("15-19岁", "15-19"), ("20-24岁", "20-24"), ("25-29岁", "25-29"),
    ("30-34岁", "30-34"), ("35-39岁", "35-39"), ("40-44岁", "40-44"),
    ("45-49岁", "45-49"), ("50-54岁", "50-54"), ("55-59岁", "55-59"),
    ("60-64岁", "60-64"), ("65-69岁", "65-69"), ("70-74岁", "70-74"),
    ("75岁及以上", "75+"),
]

SEX = [("男", "male"), ("女", "female")]

# 学历(归并到 6 档,对齐 cn_census_2020)
EDU = [
    ("未上过学", "no schooling"),
    ("小学", "primary"),
    ("初中", "junior secondary"),
    ("高中", "senior secondary"),
    ("大学专科", "junior college"),
    ("大学本科及以上", "bachelor+"),
]

MARRIAGE = [
    ("未婚", "unmarried"), ("有配偶", "married"),
    ("离婚", "divorced"), ("丧偶", "widowed"),
]

# 职业大类(7 类,七普口径)
OCCUPATION = [
    ("党政机关企事业单位负责人", "managers"),
    ("专业技术人员", "professionals"),
    ("办事人员和有关人员", "clerks"),
    ("社会生产服务和生活服务人员", "service workers"),
    ("农林牧渔生产及辅助人员", "agriculture"),
    ("生产制造及有关人员", "production workers"),
    ("不便分类的其他从业人员", "other"),
]

# 家庭规模(户规模,1~7+,来自 jiating)
HOUSEHOLD_SIZE = [
    ("一人户", "1"), ("二人户", "2"), ("三人户", "3"), ("四人户", "4"),
    ("五人户", "5"), ("六人户", "6"), ("七人及以上户", "7+"),
]

# 省份(31,对齐 cn_census_2020)
PROVINCE = [
    ("北京", "Beijing"), ("天津", "Tianjin"), ("河北", "Hebei"),
    ("山西", "Shanxi"), ("内蒙古", "Inner Mongolia"), ("辽宁", "Liaoning"),
    ("吉林", "Jilin"), ("黑龙江", "Heilongjiang"), ("上海", "Shanghai"),
    ("江苏", "Jiangsu"), ("浙江", "Zhejiang"), ("安徽", "Anhui"),
    ("福建", "Fujian"), ("江西", "Jiangxi"), ("山东", "Shandong"),
    ("河南", "Henan"), ("湖北", "Hubei"), ("湖南", "Hunan"),
    ("广东", "Guangdong"), ("广西", "Guangxi"), ("海南", "Hainan"),
    ("重庆", "Chongqing"), ("四川", "Sichuan"), ("贵州", "Guizhou"),
    ("云南", "Yunnan"), ("西藏", "Tibet"), ("陕西", "Shaanxi"),
    ("甘肃", "Gansu"), ("青海", "Qinghai"), ("宁夏", "Ningxia"),
    ("新疆", "Xinjiang"),
]


def zh_list(pairs):
    return [zh for zh, _ in pairs]


def bilingual(pairs):
    return [{"zh": zh, "en": en} for zh, en in pairs]


# 源表年龄标签 → 统一年龄段索引(B0403/B0407 用 16-19,归到 15-19)
def age_to_index(raw_label: str) -> int | None:
    s = str(raw_label).strip()
    alias = {"16-19岁": "15-19岁", "75岁及以上": "75岁及以上",
             "80-84岁": "75岁及以上", "85岁及以上": "75岁及以上",
             "75-79岁": "75岁及以上"}
    s = alias.get(s, s)
    for i, (zh, _) in enumerate(AGE_BANDS):
        if zh == s:
            return i
    return None
