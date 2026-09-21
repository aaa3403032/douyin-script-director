# AI选题证据包

用户要求截图、数据包、可复查研究过程，或热点事实容易变化时读取。截图是采集时页面状态的证据，不是来源真实性的替代品。

## 推荐目录

目录根路径和日期由当前任务决定，不写死：

```text
run/
  radar.json
  radar-ranked.json
  radar-ranked.md
  claim-ledger.csv
  evidence-manifest.csv
  evidence/
    raw/
    presentation/
  script.md
```

`radar.json` 使用新研究流程时标记 `run.schema_version=2`，并在 `run.research` 记录研究起止时间、三轮扫描名称、五类来源篮子、查询数、来源家族数、原始信号数、聚类候选数和合格数。每个最终候选还要保存三个 `talking_points`、受众收益、建议形态/时长、画面、风险边界、主讨论问题、制作可行性和下次复核/失效时间。

`rank_ai_topics.py` 会保留全部排名供审计，同时仅把达到入榜线的不重复候选放入 `selected_topics`；默认动态展示最多10个。

`raw/`保存未裁掉关键上下文的原始截图；`presentation/`保存用于视频的裁剪、放大或标注版。不能覆盖原图。

## 事实账本

`claim-ledger.csv`至少包含：

```text
claim_id,exact_claim,claim_type,source_tier,source_url,
published_at,captured_at,scope,allowed_wording,forbidden_wording,
screenshot_ids,counterevidence,status
```

`claim_type`使用已核验事实、当事方自报、合理推断、未知/冲突。`status`至少区分 verified、limited、conflicted、dropped。

## 证据清单

`evidence-manifest.csv`至少包含：

```text
evidence_id,file_path,source_url,page_title,published_at,
captured_at,timezone,region,query,time_window,metric_name,
metric_scope,claim_ids,raw_or_derived,crop_notes
```

社交互动和趋势图必须记录采集时间。没有地区或窗口的指标不能补猜；留空并写清限制。

## 每个最终候选的截图

默认采集2–4张，按可用性选择：

1. 一手事件、产品更新或研究原文；
2. 带查询词、平台、地区或窗口的趋势/互动数据；
3. 独立核验、合理反方或限制；
4. 教程结果、Demo或实际界面。

只为研究内部使用且截图没有新增证据价值时可以不截；用户明确要证据包则对缺失项标记“未采集”，不能伪造或用无关页面代替。

## 截图规范

- 原始截图保留标题、日期、指标口径和会改变理解的限定；看不到URL时在清单中记录完整URL。
- 图表依靠悬浮提示显示具体值时，把提示和坐标范围一起截入。
- 截图文件名使用稳定主题、来源和日期，不把标题中的隐私或敏感信息写入文件名。
- 社交数会变化；只能说“截至采集时页面显示”。
- 截图中的自报数字仍然是自报，不能因为截了图就升级成独立事实。
- 不截取私信、后台账号数据、私人资料或无关个人信息。发布前裁掉登录状态、头像、通知和其他不必要标识。
- 不绕过登录、验证码、付费墙、安全拦截、robots或站点限制。
- 使用截图作视频素材前检查版权、引用范围和当前平台规范；必要时只展示短暂局部并配来源。

## 数据与截图的对应

口播中的每个关键数字都应能回到一条事实账本记录；每张截图都应在证据清单中关联至少一个 `claim_id`。若截图和当前页面数值不一致，以新的带时间记录为准，不静默覆盖旧证据。

最终交付纯成稿时，不把文件路径、来源和截图说明混入口播；它们留在正文外或证据包中。
