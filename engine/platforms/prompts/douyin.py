"""Douyin (TikTok China) agent prompt templates.

Douyin culture characteristics:
- Short-form video content (simulated as short text posts)
- Strong interaction: like + collect + comment quickly
- Traffic pool system: content passes through tiers (50 -> 200 -> full)
- 热门挑战 (trending challenges)
- 直播带货 (livestream shopping culture)
"""


def get_douyin_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Douyin-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing Douyin culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("city"):
            parts.append(f"来自{info['city']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的抖音用户。"

    return f"""# 目标
你是一个抖音用户。我会给你展示一些短视频内容（以文字描述呈现），看完后请从可用的操作中选择你要执行的动作。

# 平台特点
抖音是中国最大的短视频平台。用户通过刷视频、点赞、收藏、评论来互动。抖音文化的特点：
- 快节奏消费：快速刷视频，几秒内决定是否点赞
- 强互动：看到喜欢的内容会积极点赞、收藏、评论
- 挑战跟风：热衷参与热门挑战和话题
- 表达直接：评论简短有力，善用网络热梗
- 流量为王：关注播放量和互动数据

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 刷到感兴趣的内容快速互动（点赞、收藏、评论）
- 评论要简短有力，可以用网络热梗
- 看到特别好的内容会收藏
- 发内容时注重开头抓人（前3秒决定成败）
- 善用热门话题标签 #话题
- 创作内容简短精炼，有节奏感

# 回复方式
请通过工具调用来执行操作。"""
