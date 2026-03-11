"""Source-specific prompt templates for Elite VC analysis (9.5/10 Quality)."""
from src.models.content_item import ContentItem, SourceType

# Summer Capital Investment Mandate
FOCUS_SECTORS = "Perp DEX | Stablecoin & Payment | RWA Tokenization | AI Infrastructure (Agents, Middleware, Decentralized Compute)"

JSON_SCHEMA = """请严格按照以下 JSON 格式输出，不要有任何其他文字：
{
  "summary": "业务逻辑总结(中文，约30字)",
  "category": "分类名称",
  "importance": 9,
  "action_item": "下一步可执行动作（中文，必须可落地）",
  "owner": "建议负责人（如：研究员/内容运营/工程）",
  "deadline": "截止时间（YYYY-MM-DD）",
  "expected_gain": "预期收益（中文，约30字）",
  "execution_risk": "执行风险（中文，约30字）",
  "investment_thesis": "核心投资逻辑(中文，约60字)。务必结合 Summer Capital 关注赛道。",
  "risk_factor": "潜在风险(中文，约30字)",
  "competitive_landscape": "竞对/赛道格局：它是谁的对手？在什么身位？(中文，约40字)",
  "valuation_context": "估值/融资参考：同赛道近期融资规模或二级估值对标(中文，约30字)"
}"""


def build_prompt(item: ContentItem) -> str:
    """Generate the appropriate analysis prompt based on source type."""
    if item.source == SourceType.GITHUB:
        return _github_prompt(item)
    return _news_prompt(item)


def _github_prompt(item: ContentItem) -> str:
    return f"""你是 Summer Capital 的投研负责人（VP of Research）。

投资指令：{FOCUS_SECTORS}

请深度拆解以下 GitHub 项目：
项目：{item.title}
描述：{item.description}
技术栈：{item.content_type or 'Unknown'}
增长：{item.engagement or '0'} Stars

分析任务：
1. 护城河：它是在重复造轮子，还是补齐了 AI/Web3 链条的关键环节？
2. 关联性：它是否属于我们的 Focus Sectors？若是，请给予高权重分析。
3. 评分准则：
   - 8-10分：真正的技术创新、赛道填补者、或爆发性增长的硬核项目。
   - 5-7分：优质工具、常规更新。
   - <5分：二次元/娱乐/水贴/教程（此类项目不应出现在简报中）。

{JSON_SCHEMA}"""


def _news_prompt(item: ContentItem) -> str:
    source_label = {
        SourceType.X: "X",
        SourceType.COINDESK: "CoinDesk",
        SourceType.COINTELEGRAPH: "CoinTelegraph",
        SourceType.THEBLOCK: "The Block",
        SourceType.BLOCKWORKS: "Blockworks",
    }.get(item.source, item.source.value)

    return f"""你是 Summer Capital 的投研负责人。请深度分析以下行业动态：

标题：{item.title}
来源：{source_label}
摘要：{item.description[:500]}

投资指令：{FOCUS_SECTORS}

分析任务：
1. 信号强度：这是否预示着资本流向的改变？
2. 赛道影响：对 Perp DEX 或 RWA 的合规化/流动性有何具体边际贡献？
3. 估值锚点：该消息是否改变了相关赛道的估值逻辑（例如监管放开、巨头入场）？

{JSON_SCHEMA}"""
