"""快速测试 GitHub scraper"""
from src.scrapers.github_scraper import get_ai_trending, get_web3_trending

print("🤖 AI Trending Projects:")
print("=" * 60)
ai_projects = get_ai_trending()
for i, project in enumerate(ai_projects[:5], 1):
    print(f"\n{i}. {project['repo_name']}")
    print(f"   ⭐ {project['stars']} stars today | 🔧 {project['language']}")
    print(f"   📝 {project['description'][:100]}...")
    print(f"   🔗 {project['url']}")

print("\n\n⛓️  Web3 Trending Projects:")
print("=" * 60)
web3_projects = get_web3_trending()
for i, project in enumerate(web3_projects[:5], 1):
    print(f"\n{i}. {project['repo_name']}")
    print(f"   ⭐ {project['stars']} stars today | 🔧 {project['language']}")
    print(f"   📝 {project['description'][:100]}...")
    print(f"   🔗 {project['url']}")

print(f"\n\n📊 Summary:")
print(f"   AI projects found: {len(ai_projects)}")
print(f"   Web3 projects found: {len(web3_projects)}")
