# 方法依据与取舍记录

本文件供解释方法或更新 Skill 时读取。来源最后核对日期：2026-08-31。平台规则和趋势会变化，执行具体任务时仍需实时核验。

## 一手平台资料

- [抖音算法及模型备案公示](https://lf3-cdn-tos.draftstatic.com/obj/ies-hotsoon-draft/douyin_agreement/70c3d13a-73cf-403a-8ecf-a16f70887c21.html?hide_nav_bar=1)：确认推荐会综合点击、观看时长、点赞、评论、分享、转发和“不喜欢”等行为。它没有公布固定权重、流量池人数或统一及格线，因此本 Skill 禁止把网传阈值当平台规则。
- [抖音社区自律公约](https://lf3-cdn-tos.draftstatic.com/obj/ies-hotsoon-draft/douyin_creator/40db1b96-0eb0-4754-a052-16e8325af350.html)：用于约束低质、哗众取宠和机械诱导互动。具体发布前应再核当前版本。
- [抖音用户服务协议](https://www.douyin.com/agreements/?id=6773906068725565448)：非真实AI音视频可能需要显著标识；规则具有时效性，所以 Skill 要求发布前重新查询。
- [巨量算数说明](https://www.oceanengine.com/insight/juliang-suanshu-yidongduan)：趋势应查询真实的时间、地区和人群数据，不凭记忆判断。
- [TikTok Creative Codes](https://ads.tiktok.com/business/en-US/blog/creative-best-practices-top-performing-ads)：支持“Hook—Body—Close”、尽早表达价值、字幕/画面/声音协同和快速进入主题。其研究对象主要是广告，不冒充抖音自然流量的因果规律。
- [TikTok六种叙事框架](https://ads.tiktok.com/business/en-US/blog/get-creative-6-storytelling-frameworks/)：吸收“结果前置再倒推”和原生、真实的呈现方式；不把品牌广告模板强加给个人口播。
- [YouTube内容表现说明](https://support.google.com/youtube/answer/16559650?hl=en) 与 [留存关键时刻](https://support.google.com/youtube/answer/9314415)：吸收“点击承诺—持续观看—满意度”以及根据真实留存峰谷迭代的思路，不把YouTube指标阈值移植到抖音。

## 研究依据

- [Berger & Milkman, What Makes Online Content Viral?](https://doi.org/10.1509/jmr.10.0353)：高唤醒情绪、实用性、惊奇和趣味与分享有关。研究场景不是抖音，因此只用于选择主情绪和传播价值，不用于承诺播放量。
- [Curiosity and information gaps](https://doi.org/10.1002/acp.4195) 与 [Clickbait curiosity-gap study](https://www.sciencedirect.com/science/article/pii/S0378216621000229)：具体、可回答的信息缺口能激发好奇；只隐藏答案、正文不兑现会反噬。
- [Question type and commenting intention](https://www.sciencedirect.com/science/article/pii/S0148296322005306)：问题与内容类型匹配会降低回答成本，因此实用内容问选择/判断，体验内容问经历/感受。
- [Zeigarnik effect meta-analysis](https://www.nature.com/articles/s41599-025-05000-w)：不支持把“未完成效应必然提高记忆/留存”写成定律。本 Skill 使用及时兑现的开放问题，而非无限拖延答案。

## 开源 Skill 取材边界

以下项目提供了可借鉴的工作流；本 Skill 只重构抽象方法，不复制其原句、范例库或产品推广：

- [social-media-skills/hook-writer](https://raw.githubusercontent.com/social-media-skills/skills/refs/heads/main/skills/hook-writer/SKILL.md)：从真实材料取钩子、跨机制生成多个候选、评分选优和兑现检查。
- [social-media-skills/short-form-video-script](https://raw.githubusercontent.com/social-media-skills/skills/refs/heads/main/skills/short-form-video-script/SKILL.md)：口播、画面、屏幕文字三轨和成稿后的留存检查。
- [tenfoldmarc/viral-skill](https://github.com/tenfoldmarc/viral-skill/blob/main/SKILL.md)：声音优先、受众痛点、观点先于热点、proof anchor。
- [storytelling-hooks](https://github.com/yaxeen/storytelling-skills/blob/main/skills/storytelling-hooks/SKILL.md)：钩子既要停留也要筛选正确受众，三轨首帧应互补。
- [vyralcontent/viral-hooks](https://raw.githubusercontent.com/vyralcontent/content-skills/main/skills/viral-hooks/SKILL.md)：候选应跨不同心理机制，具体性优先于文字炫技。

未纳入这些项目中缺乏可审计一手来源的断言，包括：固定3秒留存率、统一完播及格线、500人流量池、互动行为固定权重、80%静音观看、48–72小时热点窗口、固定切镜频率和“无缝循环是最强信号”。

## 本 Skill 的独有工作法

> 不承诺爆火；用真实冲突提高停留，用证据建立信任，用有代价的选择制造讨论，再让实际留存数据决定下一版。

它来自本次《Cook The Dungeon》案例的逆向验证：

- 具体事实和自然预判先建立钩子，再立刻纠正“三周做完整游戏”的误读。
- 20年设计经验、具体玩法、群体数据、行业矛盾和反方边界围绕一个母命题递进。
- “这不能证明X，但至少说明Y”的限定增强可信度，而不是削弱观点。
- 结尾把同一种AI使用放进独立创作者与大公司两个权力场景，形成真正可争论的标准测试。

这个案例是验证样本，不是所有选题的固定模板。

## Noobi.ai 改稿复盘

这次产品口播暴露了四个可迁移问题，也用于更新本 Skill：

- 首句与前十秒要分别检查；最强反转藏在第二句，仍可能在前三秒流失。
- 陌生产品名、论文名和英文术语会产生理解税；必要概念应立刻翻译成具体动作或后果。
- 观众利益不能等到后半段才出现。泛受众需要尽早知道这件事会改变自己的时间、成本、门槛、体验或选择。
- README或代码中的门禁证明某项检查被设计或实现，不等于它在所有情况下都能阻止失败，更不等于最终作品一定好。
- 泛流量评论题要经过非从业者代理测试；垂直账号则可以有意保留专业身份冲突。

这些是案例假设，不是平台定律。仍需用独立前向样本和账号真实留存、评论数据继续验证。

## AI选题雷达的取舍

2026年8月31日的前向研究同时观察了抖音原生活动、GitHub Trending、Hacker News、Reddit和公司官方公告。它暴露出三条必须固化的边界：

- 站内互动、搜索指数、GitHub Stars、下载和社区点赞描述的是不同人群、不同动作，不能相加成“全网热度”。
- 一张高互动截图只能证明抓取时的累计规模；只有同口径前后变化才能证明速度，多平台同时出现只能证明广度。
- 当前事件必须先由一手来源证明“发生了什么”，再由独立信号回答“有没有人关注”；传播潜力仍是编辑判断，不是平台推荐预测。

因此新增的 `rank_ai_topics.py` 只做去重、证据检查和“内容机会分”，不联网抓取，也不预测播放量。实时发现和截图由当前可用的检索、浏览器或平台工具完成，避免把易失效的网页结构固化成万能爬虫。

雷达设置 `balanced/news/tutorial/technical` 四个权重，是为了避免突发争议永远压过可复现教程。权重是内部决策框架，不是抖音算法权重；仍需用账号真实选题表现校准。

## Jev 漏检复盘

2026年9月21日复核时，Jev 已在9月15日公开，因而会被“只收最近30小时事件”的单窗规则排除；但最近48小时仍出现 Vercel AI Gateway 的采用数据、生态项目和多社区讨论。这个案例说明“事件发生时间”和“注意力正在加速的时间”必须拆开记录。Skill 因此改为 `breaking/rising/technical` 三轨发现：较早事件只能凭新的可核验信号进入 `rising`，不能伪装成刚发布；陌生对象也不能仅因不是大品牌而被过滤。Vercel 的采用数据属于平台方披露，仍需保留范围和归因，不能外推成全网采用率。

- [Vercel：Jev 在 AI Gateway 的发布后采用情况](https://vercel.com/blog/ai-gateway-jev-model-launch)

## 候选数与搜索深度复盘

2026年9月21日用户进一步明确：选题是口播质量的前置瓶颈，应给它更充分的实时检索；优质候选多时不应被固定 Top 5 截断。因此雷达改为三轮扫描和动态 Top 5–10，并引入覆盖饱和条件、研究漏斗和入榜资格线。

这次不把“多花时间”写成固定分钟数，因为不同日期的资讯量、网站可访性和发布截止不同。改用可审计的完成条件：三轨、五类来源篮子、主流与新对象、中文受众信号都被扫描，且连续两组新查询不再产生合格聚类。这能限制草率早停，也防止无限爬取。

动态候选数以质量门槛而非数量目标决定：默认70分、非D级、有一手事实、有具体口播节拍且制作可行。有几个合格项就展示几个，上限10个；少于5个也不用伪热点补齐。每张卡增加精确时间、三节拍口播内容、分项分、画面、有效期与不能说的结论，让用户能基于真实信息选题。
