"""Markdown report generator"""
from datetime import datetime
from typing import List, Dict
import os


class ReportBuilder:
    """生成 Markdown 格式的简报"""

    def __init__(self, output_dir: str = "outputs"):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_report(
        self,
        ai_projects: List[Dict],
        web3_projects: List[Dict],
        date: str = None
    ) -> str:
        """
        生成完整的每日简报

        Args:
            ai_projects: AI 相关项目列表（已分析）
            web3_projects: Web3 相关项目列表（已分析）
            date: 日期字符串（默认今天）

        Returns:
            生成的报告文件路径
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 按类别分组
        ai_by_category = self._group_by_category(ai_projects)
        web3_by_category = self._group_by_category(web3_projects)

        # 生成 Markdown 内容
        content = self._build_markdown(
            date=date,
            ai_by_category=ai_by_category,
            web3_by_category=web3_by_category,
            total_ai=len(ai_projects),
            total_web3=len(web3_projects)
        )

        # 保存文件
        filename = f"{date}-briefing.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _group_by_category(self, projects: List[Dict]) -> Dict[str, List[Dict]]:
        """按类别分组项目"""
        categorized = {}

        for project in projects:
            category = project.get("category", "其他")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(project)

        # 按重要性排序每个类别内的项目
        for category in categorized:
            categorized[category].sort(
                key=lambda x: x.get("importance", 0),
                reverse=True
            )

        return categorized

    def _build_markdown(
        self,
        date: str,
        ai_by_category: Dict[str, List[Dict]],
        web3_by_category: Dict[str, List[Dict]],
        total_ai: int,
        total_web3: int
    ) -> str:
        """构建 Markdown 内容"""
        lines = []

        # 标题
        lines.append(f"# Web3 + AI 每日简报 | {date}")
        lines.append("")
        lines.append(f"> 自动生成于 {datetime.now().strftime('%H:%M')} UTC+8 | ")
        lines.append(f"AI 项目 {total_ai} 条 · Web3 项目 {total_web3} 条")
        lines.append("")
        lines.append("---")
        lines.append("")

        # AI 部分
        if ai_by_category:
            lines.append("## 🤖 AI 技术进展")
            lines.append("")
            lines.extend(self._render_category_section(ai_by_category))

        # Web3 部分
        if web3_by_category:
            lines.append("## ⛓️ Web3 技术进展")
            lines.append("")
            lines.extend(self._render_category_section(web3_by_category))

        # 数据统计
        lines.append("---")
        lines.append("")
        lines.append("## 📈 今日数据")
        lines.append("")
        lines.append(f"- GitHub Trending：{total_ai + total_web3} 个相关项目")
        lines.append(f"- AI 项目：{total_ai} 个")
        lines.append(f"- Web3 项目：{total_web3} 个")
        lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*由 [Web3-AI-Daily-Brief](https://github.com/yourusername/web3-ai-daily-brief) 自动生成*")
        lines.append("")

        return "\n".join(lines)

    def _render_category_section(self, categorized: Dict[str, List[Dict]]) -> List[str]:
        """渲染分类区块"""
        lines = []

        # 按优先级排序类别（AI技术 > Web3技术 > 开发工具 > 其他）
        category_order = ["AI技术", "Web3技术", "开发工具", "其他"]
        sorted_categories = sorted(
            categorized.keys(),
            key=lambda x: category_order.index(x) if x in category_order else 999
        )

        for category in sorted_categories:
            projects = categorized[category]

            lines.append(f"### {category}")
            lines.append("")

            for project in projects:
                # 重要性星标
                stars = "⭐" * min(int(project.get("importance", 5) / 2), 5)

                lines.append(f"**{stars} [{project['repo_name']}]({project['url']})**")
                lines.append("")
                lines.append(f"- 📝 **总结**：{project['summary']}")
                lines.append(f"- 🔧 **语言**：{project.get('language', 'Unknown')}")
                lines.append(f"- 🌟 **今日 Stars**：{project.get('stars', '0')}")
                lines.append("")

        return lines
