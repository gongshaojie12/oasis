# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""YAML 分布加载器（P5: 方案 B 双语支持）。

支持两种 YAML 输入：

Plan A（兼容遗留 / 单语）::

    demographic:
      城市:
        北京: 0.6
        上海: 0.4

Plan B（新格式，单源双语）::

    demographic:
      - name: { zh: 城市, en: city }
        distribution:
          values:
            - label: { zh: 北京, en: Beijing }
              weight: 0.6
            - label: { zh: 上海, en: Shanghai }
              weight: 0.4

返回的内部规范形式 (`DistributionView`)：

- ``dist["demographic"]`` 既支持 **dict-of-trait** 访问（向后兼容：
  ``dist["demographic"]["城市"]`` → ``[("北京", 0.6), ("上海", 0.4)]``）
- 也支持 **list-of-trait-meta** 迭代/索引（新 P5 用法：
  ``list(dist["demographic"])[0]["name"]`` → ``{"zh": "城市", "en": "city"}``）

PersonaBuilder 在 ``locale="en"`` 时会通过 list 形态读取每个 trait 的双语
``label``，从而生成英文 key + 英文 value 的 persona 字典。

人口标签保留字符串；个性/媒体里"看起来像数字"的键被强制转为 float。
"""
from __future__ import annotations

import os
from typing import Any, Iterator

import yaml

_GROUPS = ("demographic", "personality", "media")


def _coerce_value(group: str, raw_key: Any) -> Any:
    if group == "demographic":
        return raw_key  # 保留原始类型（通常是字符串）
    # personality / media: 尝试转 float；不行就保留原值
    if isinstance(raw_key, str):
        try:
            return float(raw_key)
        except ValueError:
            return raw_key
    return raw_key


def _normalize_bilingual(raw: Any, *, stringify: bool = True) -> dict[str, Any]:
    """Accept str OR {zh, en} OR other → canonical {zh, en} dict.

    Missing side falls back to the other; empty input becomes empty strings.
    If ``stringify=False``, preserve original scalar types (int/float) — used
    for value labels where ``年龄: 17`` must keep the int.
    """
    if isinstance(raw, dict):
        zh = raw.get("zh")
        en = raw.get("en")
        if zh is None or zh == "":
            zh = en if en is not None and en != "" else ""
        if en is None or en == "":
            en = zh if zh is not None and zh != "" else ""
        if stringify:
            return {"zh": str(zh), "en": str(en)}
        return {"zh": zh, "en": en}
    if raw is None:
        return {"zh": "", "en": ""}
    if stringify:
        s = str(raw)
        return {"zh": s, "en": s}
    return {"zh": raw, "en": raw}


def _normalize_values(group: str, raw: Any) -> list[dict[str, Any]]:
    """Accept dict-of-weights OR list-of-{label, weight} → canonical list.

    Each item is ``{"label": {"zh": ..., "en": ...}, "weight": float}``.
    For personality/media groups, numeric-looking labels are coerced to float
    on the zh side (preserving legacy bucket semantics).
    """
    out: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        # legacy: {value: weight}
        for k, v in raw.items():
            coerced = _coerce_value(group, k)
            label = {"zh": coerced, "en": coerced}
            out.append({"label": label, "weight": float(v)})
        return out
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            raw_label = item.get("label", item.get("value", ""))
            # Preserve raw scalar types (int/float) on the value side; the
            # bilingual dict only matters when label is a {zh,en} dict.
            label = _normalize_bilingual(raw_label, stringify=False)
            # Coerce numeric-looking labels for personality/media so
            # downstream sees real floats (mirrors Plan A semantics).
            label = {
                "zh": _coerce_value(group, label["zh"]),
                "en": _coerce_value(group, label["en"]),
            }
            weight = float(item.get("weight", 0))
            out.append({"label": label, "weight": weight})
        return out
    return out


class _TraitListView:
    """Hybrid container that exposes a list of trait-meta dicts (new P5 API)
    AND a dict-of-trait-name → list-of-(value, weight) (legacy API).

    Indexing by int / iterating → trait-meta dicts.
    Indexing by str (zh trait name) → legacy list-of-tuples.
    ``in`` works against both shapes (we expose the zh names via __contains__).
    """

    __slots__ = ("_traits",)

    def __init__(self, traits: list[dict[str, Any]]):
        # _traits: [{"name": {"zh","en"}, "distribution": {"values": [...]}}]
        self._traits = traits

    # ---- list-like ---------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._traits)

    def __len__(self) -> int:
        return len(self._traits)

    # ---- dict-like (legacy) ------------------------------------------------
    def _legacy_pairs(self, trait: dict[str, Any]) -> list[tuple[Any, float]]:
        values = trait.get("distribution", {}).get("values", []) or []
        return [(v["label"]["zh"], float(v["weight"])) for v in values]

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._traits[key]
        if isinstance(key, str):
            for trait in self._traits:
                if trait["name"]["zh"] == key:
                    return self._legacy_pairs(trait)
            raise KeyError(key)
        if isinstance(key, slice):
            return self._traits[key]
        raise TypeError(f"unsupported key type: {type(key).__name__}")

    def __contains__(self, key: Any) -> bool:
        if isinstance(key, str):
            return any(t["name"]["zh"] == key for t in self._traits)
        return False

    def keys(self):
        return [t["name"]["zh"] for t in self._traits]

    def items(self):
        return [(t["name"]["zh"], self._legacy_pairs(t)) for t in self._traits]

    def values(self):
        return [self._legacy_pairs(t) for t in self._traits]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    # ---- introspection for new P5 callers ---------------------------------
    def trait_meta(self) -> list[dict[str, Any]]:
        """Direct access to the underlying list of trait-meta dicts."""
        return self._traits

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _TraitListView):
            return self._traits == other._traits
        if isinstance(other, dict):
            # Compare via legacy view for tests that pass dict literals.
            return dict(self.items()) == other
        if isinstance(other, list):
            return self._traits == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"_TraitListView({self._traits!r})"


def _build_group(group: str, raw_group: Any) -> _TraitListView:
    """Normalize a YAML group (dict or list) into a _TraitListView."""
    traits: list[dict[str, Any]] = []
    if raw_group is None:
        return _TraitListView(traits)
    if isinstance(raw_group, dict):
        # Plan A: dict of trait_name -> dict_of_weights
        for trait_name, choices in raw_group.items():
            if not isinstance(choices, dict):
                raise ValueError(
                    f"trait {group!r}.{trait_name!r} must be a mapping of "
                    f"value -> weight, got {type(choices).__name__}")
            traits.append({
                "name": _normalize_bilingual(trait_name),
                "distribution": {
                    "values": _normalize_values(group, choices),
                },
            })
        return _TraitListView(traits)
    if isinstance(raw_group, list):
        # Plan B: list of {name, distribution: {values: [...]}}
        for trait in raw_group:
            if not isinstance(trait, dict):
                continue
            name = _normalize_bilingual(trait.get("name"))
            dist = trait.get("distribution") or {}
            raw_values = dist.get("values")
            traits.append({
                "name": name,
                "distribution": {
                    "values": _normalize_values(group, raw_values),
                },
            })
        return _TraitListView(traits)
    raise ValueError(
        f"group {group!r} must be a mapping or list, got "
        f"{type(raw_group).__name__}")


def load_distribution_from_dict(raw: dict) -> dict[str, _TraitListView]:
    """Build canonical distribution view from an already-parsed dict.

    与 ``load_distribution(path)`` 等价,只是输入是 dict(yaml.safe_load 的
    产物或 DB 里存的规范化内容),不读文件 —— M1 让数据库画像也能跑模拟。
    """
    raw = raw or {}
    out: dict[str, _TraitListView] = {}
    for group in _GROUPS:
        out[group] = _build_group(group, raw.get(group))
    # 联合分布(合成个体池):若 content 含 joint 块,挂到私有键。
    # 三个 group 循环只按名取 _GROUPS,不会碰它 → 现有抽样/调用方零影响。
    try:
        from wanxiang.datasources.joint import load_joint_from_dict
        jv = load_joint_from_dict(raw)
        if jv is not None:
            out["__joint__"] = jv  # type: ignore[assignment]
    except Exception:  # pragma: no cover (defensive)
        pass
    return out


def load_distribution(path: str) -> dict[str, _TraitListView]:
    """Load a distribution YAML (Plan A or Plan B) into canonical form.

    Returns ``{"demographic": _TraitListView, "personality": _TraitListView,
    "media": _TraitListView}``. Each view supports both legacy dict-style
    access (``view["城市"]`` → ``[(value, weight), ...]``) and new
    list-style iteration (``list(view)[0]["name"]`` → ``{"zh","en"}``).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"distribution file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return load_distribution_from_dict(raw)


def validate_distribution(raw: dict) -> tuple[bool, list[str]]:
    """校验一份(已解析的)画像 dict 是否可用于造人。

    规则(宽松但够防错):
    - raw 必须是 mapping
    - 三组 demographic/personality/media 至少有一组非空
    - 每个 trait 必须能取出 name + 至少一个 value
    - 每个 value 的 weight 必须是 >0 的数

    返回 ``(ok, errors)``;ok=False 时 errors 列出问题(供前端回显)。
    """
    errors: list[str] = []
    if not isinstance(raw, dict):
        return False, ["顶层必须是映射(demographic/personality/media)"]

    groups_present = [g for g in _GROUPS if raw.get(g)]
    if not groups_present:
        errors.append(
            "至少需要 demographic / personality / media 其中一组非空")

    for group in _GROUPS:
        rg = raw.get(group)
        if rg is None:
            continue
        if not isinstance(rg, (dict, list)):
            errors.append(f"{group} 必须是映射或列表")
            continue
        # 统一成 (trait_name, values) 迭代
        if isinstance(rg, dict):
            iterable = list(rg.items())
        else:
            iterable = []
            for t in rg:
                if not isinstance(t, dict):
                    errors.append(f"{group} 的每个 trait 必须是映射")
                    continue
                nm = t.get("name")
                vals = ((t.get("distribution") or {}).get("values"))
                iterable.append((nm, vals))
        for trait_name, choices in iterable:
            label = trait_name if isinstance(trait_name, str) else (
                (trait_name or {}).get("zh") if isinstance(trait_name, dict)
                else str(trait_name))
            if not label:
                errors.append(f"{group} 有 trait 缺少 name")
            # 取出 (value, weight) 对
            pairs = []
            if isinstance(choices, dict):
                pairs = list(choices.items())
            elif isinstance(choices, list):
                for v in choices:
                    if isinstance(v, dict):
                        pairs.append((v.get("label"), v.get("weight")))
            if not pairs:
                errors.append(f"{group}.{label} 没有任何取值")
                continue
            for _val, w in pairs:
                try:
                    wf = float(w)
                except (TypeError, ValueError):
                    errors.append(f"{group}.{label} 的权重非数字: {w!r}")
                    continue
                if wf <= 0:
                    errors.append(f"{group}.{label} 的权重必须 >0: {wf}")

    return (len(errors) == 0), errors
