"""Source-specific prompt templates for Gemini analysis"""
from src.models.content_item import ContentItem, SourceType

# Investment-oriented categories (VC perspective)
CATEGORIES_GITHUB = "前沿技术/DeFi交易/支付稳定币/RWA资产代币化/基础设施/开发者工具/其他"
CATEGORIES_NEWS = "前沿技术/DeFi交易/支付稳定币/RWA资产代币化/融资动态/市场动态/监管政策/其他"

JSON_SCHEMA = """\u8bf7\u4e25\u683c\u6309\u7167\u4ee5\u4e0b JSON \u683c\u5f0f\u8f93\u51fa\uff0c\u4e0d\u8981\u6709\u4efb\u4f55\u5176\u4ed6\u6587\u5b57\uff1a
{{
  "summary": "\u9879\u76ee\u7684\u4e00\u53e5\u8bdd\u603b\u7ed3",
  "category": "\u5206\u7c7b\u540d\u79f0",
  "importance": 8
}}"""


def build_prompt(item: ContentItem) -> str:
    """Generate the appropriate analysis prompt based on source type."""
    if item.source == SourceType.GITHUB:
        return _github_prompt(item)
    return _news_prompt(item)


def _github_prompt(item: ContentItem) -> str:
    return f"""请从VC投资视角分析以下GitHub项目：

项目名称：{item.title}
描述：{item.description}
编程语言：{item.content_type or 'Unknown'}
今日 Stars：{item.engagement or '0'}

请提供：
1. 一句话总结（中文，<30字，突出商业价值）
2. 分类（从以下选择一个）：{CATEGORIES_GITHUB}
3. 投资相关性评分（1-10，考虑：技术创新度、市场潜力、是否有真实收入可能、适合投资阶段）

{JSON_SCHEMA}"""


def _news_prompt(item: ContentItem) -> str:
    source_label = {
        SourceType.COINDESK: "CoinDesk",
        SourceType.COINTELEGRAPH: "CoinTelegraph",
    }.get(item.source, item.source.value)

    return f"""请从VC投资视角分析以下加密/Web3行业新闻：

标题：{item.title}
来源：{source_label}
摘要：{item.description[:300]}
发布时间：{item.published_date or '未知'}

请提供：
1. 一句话总结（中文，<30字，突出对投资决策的影响）
2. 分类（从以下选择一个）：{CATEGORIES_NEWS}
3. 投资相关性评分（1-10，考虑：对市场影响、监管影响、是否涉及融资/退出、对重点赛道的影响）

{JSON_SCHEMA}"""
