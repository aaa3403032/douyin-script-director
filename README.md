# 抖音口播导演

`douyin-script-director` 是一个面向 Codex 的中文抖音口播创作 Skill。它把主题、新闻、网页、评论、视频和现有文案重构为可直接拍摄的口播稿，重点优化强钩子、信息节拍、事实可信度、严格时长和评论互动。

## 核心能力

- 先确定目标观众、观看收益、母命题和中心矛盾，再搭建结构。
- 跨不同心理机制生成钩子，并检查最强信息是否真正落在首句。
- 区分已核验事实、当事方自报、合理推断和未知信息。
- 区分产品设计、代码机制、单次演示与普遍效果，避免夸大保证。
- 控制陌生术语的理解成本，并在前段说明内容与观众的关系。
- 按目标时长估算口播字量，通过脚本检查机械风险。
- 结尾只保留一个双方都能自圆其说的评论问题。

## 安装

```bash
git clone https://github.com/aaa3403032/douyin-script-director.git ~/.codex/skills/douyin-script-director
```

重新打开 Codex 后，可直接在请求中使用：

```text
使用 $douyin-script-director，把下面的主题写成一条两分钟抖音口播，只要完整成稿。
```

## 目录

- `SKILL.md`：技能入口、工作流和核心门禁。
- `references/`：叙事架构、事实研究、质量门禁和方法依据。
- `scripts/audit_oral_script.py`：时长、首句、术语、绝对化说法和结尾问题的机械检查。
- `agents/openai.yaml`：Codex 界面元数据。

## 校验

```bash
python3 scripts/audit_oral_script.py draft.txt --target 120
```

机械检查不能判断创意、事实真伪或真实流量表现。时效事实仍需实时核验，发布结果也会受到选题、账号、画面、表演、剪辑和受众匹配影响。

