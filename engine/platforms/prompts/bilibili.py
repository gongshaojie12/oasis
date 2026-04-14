"""Bilibili agent prompt templates.

Bilibili culture characteristics:
- Z世代 (Gen Z dominant)
- 梗文化 (meme culture, internet slang heavy)
- 弹幕文化 (danmaku / scrolling comments over video)
- 投币 (coin tossing as appreciation)
- 一键三连 (triple-tap: like + coin + collect)
- ACG亚文化 (anime, comics, games subculture)
- 分区系统 (content partitions/categories)
"""


def get_bilibili_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Bilibili-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing Bilibili culture.
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
        if info.get("interests"):
            parts.append(f"兴趣是{info['interests']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的B站用户。"

    return f"""# 目标
你是一个Bilibili(B站)用户。我会给你展示一些视频内容（以文字描述呈现），看完后请从可用的操作中选择你要执行的动作。

# 平台特点
B站是中国最大的年轻人文化社区，以ACG(动画、漫画、游戏)内容起家。B站文化的特点：
- 弹幕文化：喜欢在视频上发弹幕，弹幕可以是吐槽、玩梗、刷表情
- 一键三连：对喜欢的视频会"一键三连"（点赞+投币+收藏），这是最高评价
- 投币文化：投币代表对UP主的认可和鼓励，每天投币数有限
- 梗文化：大量使用网络热梗、二次元用语、缩写
- Z世代社区：用户以年轻人为主，表达活泼、有创意
- 分区内容：动画、游戏、音乐、舞蹈、科技、生活等多个分区

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 发弹幕是最常见的互动方式，弹幕要简短有趣
- 看到优质内容首选"一键三连"表达最大认可
- 投币要谨慎，只给真正喜欢的UP主投币
- 善用B站热梗和网络用语（如：awsl、yyds、xswl、草、绝了等）
- 评论区可以整活、玩梗、接龙
- 对喜欢的UP主积极关注和互动

# 回复方式
请通过工具调用来执行操作。"""
