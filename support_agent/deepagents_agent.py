"""deepagents 框架接入（可选）。

用 LangChain 的 deepagents 框架创建一个「自动回复 Agent」：
- 内置 planning / subagents / filesystem 等能力（框架自带）；
- 挂载自定义工具 search_knowledge_base，让 Agent 从知识库向量库检索答案。

依赖：pip install deepagents langchain-openai
未安装或未配置大模型时，自动降级为内置 RAG 逻辑，不影响系统运行。
"""
try:
    from deepagents import create_deep_agent  # noqa: F401
    DEEPAGENTS_AVAILABLE = True
except Exception:
    DEEPAGENTS_AVAILABLE = False

from llm import get_llm_config, llm_ready

SYSTEM_PROMPT = (
    "你是企业内部 IT 支持 Agent。回答用户问题前，必须先调用 search_knowledge_base "
    "检索内部知识库，再基于检索结果给出分步骤、专业、简洁的解答。"
    "若知识库内容不足，请如实说明并建议转人工。"
)


def run_auto_reply_agent(query):
    """使用 deepagents 生成自动回复；不可用返回 None。"""
    if not DEEPAGENTS_AVAILABLE or not llm_ready():
        return None
    try:
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI
        from langchain_core.tools import tool
        from knowledge import retrieve  # 运行期导入，避免循环依赖

        cfg = get_llm_config()
        model = ChatOpenAI(
            model=cfg["model"],
            api_key=cfg["api_key"],
            base_url=cfg["base_url"] or None,
            temperature=cfg["temperature"],
        )

        @tool
        def search_knowledge_base(q: str) -> str:
            """在内部知识库向量库中检索与问题相关的内容。"""
            hits = retrieve(q, k=3)
            if not hits:
                return "未检索到相关内容。"
            lines = []
            for h in hits:
                title = h["metadata"].get("title", "")
                lines.append(f"- [{h['metadata'].get('kb_id','')}] {title} (相似度 {h['score']:.3f})")
            return "\n".join(lines)

        agent = create_deep_agent(
            tools=[search_knowledge_base],
            model=model,
            system_prompt=SYSTEM_PROMPT,
        )
        result = agent.invoke({"messages": [{"role": "user", "content": query}]})
        for m in reversed(result.get("messages", [])):
            if getattr(m, "type", "") == "ai" and getattr(m, "content", ""):
                return m.content
        return None
    except Exception:
        return None
