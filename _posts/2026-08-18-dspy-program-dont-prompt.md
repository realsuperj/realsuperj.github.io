---
title: DSPy：别再手搓 Prompt 了，把任务"声明"出来
date: 2026-08-18 15:30:00 +0800
categories: [技术]
tags: [DSPy, LLM, AI, Prompt]
---

写 LLM 应用，最磨人的常常是那段 prompt：措辞、格式、解析，换个模型还得重调一遍。手搓久了就会想，这件事能不能别写在字符串里。

[dspy.ai](https://dspy.ai/) 首页一句话，说的就是这个：

> **Program, don't prompt, your LLMs.**

编程，而不是写提示词。你声明任务结构，框架负责怎么跟模型说话。

<!--more-->

## 先看它是什么

DSPy 是斯坦福 NLP 团队做的一个 Python 框架，2022 年 12 月起在开源社区中持续迭代至今。核心主张是：与其手写一大堆易碎、难维护的 prompt 字符串，不如把任务定义成**结构化的代码**，让框架去处理"到底怎么跟模型说话"这一层。

三个核心概念：

- **Signature（签名）**：用带类型的输入 / 输出声明任务。比如"输入一封邮件，输出事件名和日期"。
- **Module（模块）**：同一个签名，可以换不同的执行策略——直接问（`Predict`）、加思维链（`ChainOfThought`）、带工具的推理循环（`ReAct`）。任务定义本身不用动。
- **Optimizer（优化器）**：给一批样例和一个评分函数，它自动帮你"编译"、调优 prompt，直到效果收敛。

说白了，就是把「要做什么」和「怎么跟模型说话」拆开。

## 举个具体的例子

任务很简单：给一段邮件文本，提取出事件名称和日期。比如这样一段：

```python
email_text = """
Hi team, reminder that the Q3 planning offsite is this Thursday, June 5.
We'll start at 10am in the downtown office. Please RSVP by Wednesday.
"""
```

期望拿到的是：`event_name = "Q3 planning offsite"`，`date = "Thursday, June 5"`。

### 传统写法

```python
import openai
import json

def extract_event(email_text):
    prompt = f"""你是一个信息提取助手。请从下面的邮件中提取事件名称和日期。
请严格按照如下 JSON 格式输出，不要输出任何其他内容：
{{"event_name": "...", "date": "..."}}

邮件内容：
{email_text}

输出："""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content

    # 还得自己解析、自己兜底
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 模型有时候会多说一句话，或者裹一层 markdown 代码块
        raw = raw.strip().removeprefix("```json").removesuffix("```")
        return json.loads(raw)
```

这种写法的问题主要集中在几个细节上：

- prompt 是拼字符串，格式说明全靠手写和运气，模型输出稍有偏差，就得回来加正则、加兜底
- 想让效果更好——加思维链、塞 few-shot 示例——只能往 prompt 里继续堆，越改越乱
- 换个模型（GPT-4o 换 Claude），辛苦调好的 prompt 效果可能直接掉下来，得重调一遍
- 没有任何自动化手段去"优化"它，全靠人工试错

### DSPy 写法

```python
import dspy

lm = dspy.LM("openai/gpt-4o")
dspy.configure(lm=lm)

class ExtractEvent(dspy.Signature):
    """Extract event details from an email."""
    email: str = dspy.InputField()
    event_name: str = dspy.OutputField()
    date: str = dspy.OutputField()

extract = dspy.Predict(ExtractEvent)
result = extract(email=email_text)

print(result.event_name, result.date)
# Q3 planning offsite  Thursday, June 5
```

就这些。`result` 直接是结构化对象，不用自己 `json.loads`，也不用处理模型附带多余输出的情况——怎么把这个声明变成实际发给模型的 prompt、怎么把返回文本解析回结构，是框架内部的 Adapter 在做。

### 摆在一起看

| | 传统 Prompt | DSPy |
|---|---|---|
| 任务定义 | 拼字符串 | 声明式的输入 / 输出类型（Signature） |
| 输出解析 | 自己写 JSON 解析和兜底 | 框架处理，直接拿到结构化对象 |
| 换策略 | 重写整个 prompt | 换一行：`dspy.ChainOfThought(...)` |
| 换模型 | 基本要重调 prompt | 通常只改 `dspy.LM(...)` 里的模型名 |
| 提升效果 | 人工加示例、反复试 | 用优化器，给样例 + 评分函数自动调 |

## 换策略只需要改一行

这是它在日常迭代中最实用的一点。比如直接抽取效果不够好，想让模型先推理再输出：

```python
extract = dspy.ChainOfThought(ExtractEvent)
```

想让它能调工具、跑推理循环：

```python
extract = dspy.ReAct(ExtractEvent, tools=[search])  # search 是你自己写的检索函数
```

`ExtractEvent` 这个 Signature 一个字都不用改。在传统写法里，这两处调整都意味着重写整段 prompt，还要重新调整格式说明和兜底逻辑。

## 自动优化：把调 prompt 交给框架

```python
# metric 是你自己写的评分函数，比如抽取结果和标注是否一致
optimizer = dspy.GEPA(metric=accuracy_metric, auto="medium")
optimized = optimizer.compile(extract, trainset=labeled_emails)

optimized.save("extract_v2.json")
```

官网给的那组数字是：同一个 gpt-5.4-mini，zero-shot 基线 62%，用 GEPA 编译之后 89%，用了 200 条样例、成本 2.18 美元。

这一步在手写 prompt 的方式下基本无法自动化——只能靠人反复换措辞、观察效果，再凭经验判断是否真的有提升。DSPy 把它变成了"给数据 + 给评分标准，框架自己去搜索更好的 prompt / few-shot 组合"。

## 本质上它替你做了什么

概括起来就是：**你只负责声明"有什么输入、要什么输出"，中间怎么把它包装成模型能理解的 prompt、以及怎么把模型返回的文本解析回目标结构，都由框架负责。**

以前得自己做的：想指令措辞 → 拼 prompt 字符串 → 在 prompt 里说明 JSON 格式还得举例 → 写解析和容错代码 → 效果不好就回去改措辞反复试。

现在要做的：写个 Signature，声明输入输出字段和类型。剩下的交给框架。

这层解耦带来的连锁好处才是关键——换模型、换策略都变轻了，因为你维护的是"任务是什么"，而不是"这次跟这个模型该怎么说话"。

## 适不适合用

官网数据：月下载量 640 万+、444 位贡献者、3.7 万 GitHub star。生产环境里 Databricks、Shopify、Dropbox、AWS、JetBlue、Replit 都在用，Shopify 拿它做全店铺的元数据抽取，官网写的是成本降低约 550 倍。

当然它也有不适用的场景：如果只是写个一次性的小脚本，直接调 API 大概率更快，多引一层框架并不划算。DSPy 的价值主要体现在任务本身有一定复杂度、需要频繁迭代、或者后续可能换模型换策略的场景——这时少维护的是 prompt，而不只是少写几行代码。

---

相关链接：[dspy.ai](https://dspy.ai/) · [GitHub](https://github.com/stanfordnlp/dspy)
