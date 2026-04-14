import { success } from '~~/server/utils/response'

const PLATFORMS = [
  { id: 'twitter', name: 'Twitter', nameZh: '推特', language: 'en', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'quote_post'] },
  { id: 'reddit', name: 'Reddit', nameZh: 'Reddit', language: 'en', actions: ['like_post', 'dislike_post', 'create_post', 'create_comment', 'like_comment', 'dislike_comment', 'search_posts', 'search_user', 'trend', 'refresh', 'do_nothing', 'follow', 'mute'] },
  { id: 'weibo', name: 'Weibo', nameZh: '微博', language: 'zh-CN', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'quote_post'] },
  { id: 'xiaohongshu', name: 'Xiaohongshu', nameZh: '小红书', language: 'zh-CN', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'collect_post', 'share_post'] },
  { id: 'douyin', name: 'Douyin', nameZh: '抖音', language: 'zh-CN', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'collect_post'] },
  { id: 'kuaishou', name: 'Kuaishou', nameZh: '快手', language: 'zh-CN', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'send_gift', 'post_shuoshuo'] },
  { id: 'bilibili', name: 'Bilibili', nameZh: 'B站', language: 'zh-CN', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'send_danmaku', 'give_coin', 'triple_tap'] },
  { id: 'wechat_video', name: 'WeChat Video', nameZh: '微信视频号', language: 'zh-CN', actions: ['create_post', 'like_post', 'repost', 'follow', 'do_nothing', 'share_to_friends'] },
]

export default defineEventHandler(async () => {
  return success(PLATFORMS)
})
