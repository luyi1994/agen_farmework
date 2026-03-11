# Python 通用 Agent 框架 —— 架构设计方案

> 版本：v1.1 | 日期：2026-03-09 | 状态：待审核

---

## 一、总体目标

构建一个**生产可用的通用 Python Agent 框架**，具备以下特性：

- 多 LLM 后端自由切换（Claude / OpenAI / Gemini / 本地模型）
- 工具调用（Tool Use）标准化注册与执行
- **Skill 层**：可复用的多步骤组合能力，位于 Agent 与 Tool 之间
- 双层记忆系统（短期会话记忆 + 长期向量记忆）
- 联网搜索能力
- 可通过 API / CLI 两种方式使用

---

## 二、技术选型

| 层级 | 选型 | 说明 |
|------|------|------|
| LLM 统一接口 | **LiteLLM** | 100+ 模型统一调用，无缝切换 |
| Agent 编排 | **LangGraph** | 基于图的 Agent 状态机，支持循环推理 |
| 短期记忆 | **Redis** / 内存 dict | 会话级对话历史，TTL 自动过期 |
| 长期记忆 | **ChromaDB** | 本地向量数据库，无需外部服务 |
| Embedding | **sentence-transformers** | 本地嵌入，也可对接 OpenAI Embedding |
| 联网搜索 | **Tavily API** / **DuckDuckGo** | Tavily 精度高，DDG 免费备选 |
| API 服务 | **FastAPI** | 对外提供 REST 接口 |
| 配置管理 | **Pydantic Settings** | 环境变量 + `.env` 文件 |
| 日志 | **Loguru** | 结构化日志，开箱即用 |

---

## 三、目录结构

```
agent_framework/
│
├── main.py                     # 入口：CLI 启动
├── .env.example                # 环境变量模板
├── requirements.txt
├── pyproject.toml
│
├── config/
│   └── settings.py             # 全局配置（LLM、记忆、工具开关）
│
├── core/                       # 核心 Agent 逻辑
│   ├── __init__.py
│   ├── agent.py                # Agent 主类：组装所有模块
│   ├── graph.py                # LangGraph 状态图定义（推理循环）
│   └── state.py                # AgentState 数据结构
│
├── llm/                        # LLM 适配层
│   ├── __init__.py
│   ├── base.py                 # LLMProvider 抽象基类
│   └── litellm_provider.py     # LiteLLM 实现（统一入口）
│
├── memory/                     # 记忆系统
│   ├── __init__.py
│   ├── base.py                 # 记忆抽象基类
│   ├── short_term.py           # 短期记忆：对话历史窗口
│   └── long_term.py            # 长期记忆：向量检索存储
│
├── tools/                      # 共享工具池（跨 Skill 通用的原子操作）
│   ├── __init__.py
│   ├── base.py                 # Tool 抽象基类 + @tool 装饰器
│   ├── registry.py             # 全局工具注册中心
│   └── shared/                 # 公共工具（多个 Skill 共用）
│       ├── web_search.py       # 联网搜索（research / write_report 共用）
│       └── file_ops.py         # 文件读写（data_analysis / write_report 共用）
│
├── skills/                     # Skill 系统（每个 Skill 是自包含的包）
│   ├── __init__.py
│   ├── base.py                 # Skill 抽象基类
│   ├── registry.py             # Skill 注册中心
│   │
│   ├── research/               # Skill：深度调研
│   │   ├── __init__.py
│   │   ├── skill.py            # ResearchSkill 主逻辑
│   │   └── tools/              # 该 Skill 专属工具
│   │       └── content_extractor.py  # 网页正文提取
│   │
│   ├── summarize/              # Skill：长文摘要
│   │   ├── __init__.py
│   │   ├── skill.py
│   │   └── tools/
│   │       └── text_chunker.py       # 文本分段工具
│   │
│   ├── data_analysis/          # Skill：数据分析
│   │   ├── __init__.py
│   │   ├── skill.py
│   │   └── tools/
│   │       └── calculator.py         # 统计计算工具
│   │
│   └── write_report/           # Skill：生成报告
│       ├── __init__.py
│       ├── skill.py
│       └── tools/
│           └── formatter.py          # Markdown/PDF 格式化
│
├── api/                        # REST API 层（可选部署）
│   ├── __init__.py
│   ├── server.py               # FastAPI app
│   └── routes/
│       ├── chat.py             # POST /chat
│       └── memory.py           # GET/DELETE /memory
│
├── utils/
│   ├── logger.py               # Loguru 日志配置
│   └── helpers.py
│
└── tests/
    ├── test_tools.py
    ├── test_memory.py
    └── test_agent.py
```

---

## 四、核心模块详细设计

### 4.1 LLM 层（`llm/`）

**目标：** 一处配置，随意切换模型。

```
LLMProvider (base.py)
    └── LiteLLMProvider (litellm_provider.py)
            ├── chat(messages) -> str
            ├── stream(messages) -> Iterator
            └── bind_tools(tools) -> LLM with tools
```

**配置切换示例（.env）：**
```env
# 切换模型只需改这一行
LLM_MODEL=claude-sonnet-4-6          # Anthropic Claude
# LLM_MODEL=gpt-4o                   # OpenAI
# LLM_MODEL=gemini/gemini-1.5-pro    # Google
# LLM_MODEL=ollama/llama3.1          # 本地 Ollama
```

LiteLLM 自动路由到对应服务，Agent 代码**零改动**。

---

### 4.2 工具系统（`tools/`）

**目标：** 用装饰器一行注册工具，自动生成 LLM 可识别的 JSON Schema。

**注册方式：**
```python
# tools/web_search.py
@tool(name="web_search", description="搜索互联网获取最新信息")
def web_search(query: str) -> str:
    ...

# tools/calculator.py
@tool(name="calculator", description="执行数学计算")
def calculate(expression: str) -> str:
    ...
```

**工具注册中心（registry.py）：**
```
ToolRegistry
    ├── register(tool_fn)       # 注册工具
    ├── get_all_schemas()       # 输出 LLM Tool Schema 列表
    ├── execute(name, args)     # 执行工具调用
    └── list_tools()            # 列出所有可用工具
```

**内置工具清单：**

| 工具名 | 功能 | 依赖 |
|--------|------|------|
| `web_search` | Tavily / DDG 联网搜索 | tavily-python |
| `calculator` | 安全数学表达式计算 | 内置 |
| `file_read` | 读取本地文件 | 内置 |
| `file_write` | 写入本地文件 | 内置 |
| `memory_save` | 主动存入长期记忆 | ChromaDB |
| `memory_recall` | 主动检索长期记忆 | ChromaDB |

---

### 4.3 Skill 系统（`skills/`）

**目标：** 在 Tool（原子操作）之上提供可复用的多步骤组合能力，Agent 可直接调用 Skill 完成复杂任务，无需每次从零规划。

#### Tool vs Skill 的本质区别

```
Tool（原子）：  web_search(query) → 返回搜索结果字符串
Skill（组合）： ResearchSkill(topic)
                  → web_search × N 轮          ← 调用共享 Tool
                  → content_extractor(url)     ← 调用自己私有 Tool
                  → LLM 摘要整合
                  → memory_save 存入长期记忆
                  → 返回结构化研究报告
```

#### 工具归属策略

```
tools/shared/          ← 公共工具：多个 Skill 都要用（如 web_search、file_ops）
skills/research/tools/ ← 私有工具：仅 ResearchSkill 内部使用（如 content_extractor）
skills/summarize/tools/← 私有工具：仅 SummarizeSkill 内部使用（如 text_chunker）
```

**原则：**
- 工具**只服务于一个 Skill** → 放在该 Skill 的 `tools/` 目录下（私有）
- 工具**被多个 Skill 共用** → 放在 `tools/shared/` 目录下（公共）
- Skill 内部调用工具时优先用自己的私有工具，不够再引用公共工具池

#### Skill 抽象基类（base.py）

```python
class BaseSkill:
    name: str              # Skill 名称
    description: str       # 供 LLM 理解的功能描述
    required_tools: list   # 依赖的 Tools 列表

    async def run(self, **kwargs) -> SkillResult:
        """执行 Skill 主逻辑（可内部调用多个 Tool）"""
        raise NotImplementedError

    def to_tool_schema(self) -> dict:
        """将 Skill 暴露为 LLM 可识别的 Tool Schema"""
        ...
```

> **关键设计：** Skill 对 LLM 来说**就是一个 Tool**，LLM 无需知道内部实现了几步，直接调用即可。

#### Skill 注册中心（registry.py）

```
SkillRegistry
    ├── register(skill_cls)          # 注册 Skill 类
    ├── get_all_schemas()            # 输出所有 Skill 的 Tool Schema
    ├── execute(name, kwargs)        # 执行指定 Skill
    └── list_skills()               # 列出所有 Skill
```

**工具加载顺序：**
1. `tools/shared/` 中的公共工具自动注册到全局 ToolRegistry
2. 每个 Skill 初始化时，加载自身 `tools/` 下的私有工具到**局部工具池**
3. Skill 执行时优先查找自身私有工具，未找到则 fallback 到全局公共工具池
4. SkillRegistry 将所有 Skill 暴露为 Tool Schema，交给 LLM 统一调用

> LLM 视角下 Skill 就是 Tool，完全无感知内部实现几层。

#### 内置 Skill 清单

| Skill 名 | 功能描述 | 内部使用的 Tools |
|----------|----------|-----------------|
| `research` | 多轮搜索 + 整合摘要 + 存入记忆 | `web_search` × N, `memory_save` |
| `summarize` | 长文本自动分段摘要 | `file_read`（可选）|
| `data_analysis` | 读取数据文件 + 统计计算 + 生成报告 | `file_read`, `calculator`, `file_write` |
| `write_report` | 调研主题 + 生成结构化报告文件 | `research`, `file_write` |

#### Skill 执行流（以 `research` 为例）

```
Agent 调用 ResearchSkill(topic="量子计算最新进展")
        │
        ▼
① web_search("量子计算 2026 最新") → 结果1
② web_search("quantum computing breakthrough") → 结果2
③ LLM 摘要整合结果1 + 结果2
④ memory_save(摘要内容, metadata={topic, date})
        │
        ▼
返回 SkillResult {
    summary: "...",
    sources: [...],
    memory_id: "xxx"
}
```

#### Skill 的注册方式（装饰器）

```python
# skills/research.py
@skill(name="research", description="对某个主题进行多轮深度调研并存入记忆")
class ResearchSkill(BaseSkill):
    required_tools = ["web_search", "memory_save"]

    async def run(self, topic: str, max_rounds: int = 3) -> SkillResult:
        ...
```

---

### 4.4 记忆系统（`memory/`）

#### 短期记忆（short_term.py）

- **存储：** 内存 `deque` 或 Redis（生产推荐）
- **作用：** 保存当前会话的对话历史（最近 N 轮）
- **特性：**
  - 按 `session_id` 隔离
  - 可配置最大窗口长度（默认 20 轮）
  - Redis 模式支持 TTL 自动过期（默认 1 小时）

```
ShortTermMemory
    ├── add(role, content, session_id)
    ├── get_history(session_id) -> List[Message]
    ├── clear(session_id)
    └── trim(session_id, max_turns)
```

#### 长期记忆（long_term.py）

- **存储：** ChromaDB（本地持久化）
- **作用：** 跨会话保存重要信息，语义相似度检索
- **写入时机：**
  1. Agent 主动调用 `memory_save` 工具
  2. 每轮对话结束后自动摘要存储（可配置开关）

```
LongTermMemory
    ├── save(text, metadata)             # 存入向量库
    ├── search(query, top_k=5) -> List   # 语义搜索
    ├── delete(memory_id)
    └── clear_all()
```

**记忆融合策略（在 Agent 推理前执行）：**
```
用户输入
    ↓
① 检索长期记忆（相关历史知识）
② 读取短期记忆（当前会话上下文）
    ↓
组合成 Prompt Context → 发给 LLM
```

---

### 4.4 Agent 核心（`core/`）

采用 **LangGraph** 构建有状态的推理图：

```
                    ┌─────────────────────────────┐
                    │         AgentState           │
                    │  - messages (对话历史)        │
                    │  - session_id                │
                    │  - retrieved_memory (检索结果) │
                    │  - tool_calls (待执行工具)    │
                    │  - final_answer              │
                    └─────────────────────────────┘

推理循环（Graph）：

  [START]
     ↓
[memory_retrieve]  ← 从长期记忆检索相关信息
     ↓
[llm_call]         ← LLM 推理，决定：直接回答 or 调用工具
     ↓
  ┌──┴──────────────────┐
  │ 有工具调用？         │
  YES                   NO
  ↓                     ↓
[tool_executor]      [memory_save]  ← 存储重要信息到长期记忆
  ↓                     ↓
[llm_call]            [END]
  (继续推理)
```

---

### 4.5 配置系统（`config/settings.py`）

```python
class Settings(BaseSettings):
    # LLM
    llm_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # 短期记忆
    short_term_backend: str = "memory"   # "memory" | "redis"
    short_term_max_turns: int = 20
    redis_url: str = "redis://localhost:6379"

    # 长期记忆
    long_term_enabled: bool = True
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"

    # 工具
    search_provider: str = "tavily"      # "tavily" | "duckduckgo"
    tavily_api_key: str = ""

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
```

---

## 五、数据流图

```
用户输入 (CLI / API)
        │
        ▼
  ┌─────────────┐
  │  Agent.run()│
  └──────┬──────┘
         │
         ├─► ShortTermMemory.get_history()    → 会话历史
         ├─► LongTermMemory.search()          → 相关长期记忆
         │
         ▼
  ┌──────────────────────────────────────────┐
  │  LLM 推理                                 │
  │  Schema = 公共 Tools + 所有 Skill Schema  │
  └───────────────────┬──────────────────────┘
                      │
          ┌───────────┴────────────┐
          │  LLM 返回调用目标？     │
          └───────────┬────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   调用公共 Tool    调用 Skill     直接回答
   (web_search)   (research)         │
        │             │              ▼
        │         ┌───┴──────────────────────────┐
        │         │  Skill 内部执行               │
        │         │  ① 私有 Tool（content_extractor）│
        │         │  ② 公共 Tool（web_search）     │
        │         │  ③ 内部 LLM 摘要              │
        │         │  ④ memory_save                │
        │         └───────────────┬──────────────┘
        │                         │
        └────────────┬────────────┘
                     ▼
            工具/Skill 执行结果
                     │
                     ▼
            回注 LLM 继续推理
                     │
                     ▼
              ShortTermMemory.add()
              LongTermMemory.save()（可选）
                     │
                     ▼
                  输出给用户
```

**架构层次总览：**

```
┌─────────────────────────────────────────────┐
│                  Agent（LangGraph）           │  ← 编排层
├─────────────────────────────────────────────┤
│   LLM（LiteLLM）  │  Memory（短期 + 长期）   │  ← 核心能力层
├──────────────┬──────────────────────────────┤
│   Skill 层   │  research / summarize / ...  │  ← 组合能力层
│  (含私有 Tool)│  skills/*/tools/             │
├──────────────┴──────────────────────────────┤
│   公共 Tool 层    tools/shared/              │  ← 原子操作层
└─────────────────────────────────────────────┘
```

---

## 六、API 接口设计

### POST `/chat`
```json
Request:
{
  "session_id": "user_123",
  "message": "帮我搜索最新的 AI 新闻",
  "stream": false
}

Response:
{
  "session_id": "user_123",
  "reply": "...",
  "tool_calls_used": ["web_search"],
  "memory_retrieved": 2
}
```

### GET `/memory/{session_id}`
返回当前会话短期记忆历史。

### DELETE `/memory/{session_id}`
清除指定会话的短期记忆。

### GET `/tools`
返回所有已注册工具列表及 Schema。

---

## 七、依赖清单（requirements.txt）

```
# 核心框架
langgraph>=0.2.0
langchain-core>=0.3.0
litellm>=1.40.0

# 记忆
chromadb>=0.5.0
sentence-transformers>=3.0.0
redis>=5.0.0           # 可选，短期记忆 Redis 后端

# 工具
tavily-python>=0.3.0   # 联网搜索
duckduckgo-search>=6.0.0  # 备用搜索

# API
fastapi>=0.111.0
uvicorn>=0.30.0

# 工具链
pydantic>=2.7.0
pydantic-settings>=2.3.0
loguru>=0.7.0
python-dotenv>=1.0.0
```

---

## 八、扩展路线图

| 阶段 | 功能 | 优先级 |
|------|------|--------|
| v1.0 | 核心工具调用 + 双层记忆 + 联网搜索 | 必须 |
| v1.1 | 多 Agent 协作（Supervisor 模式） | 高 |
| v1.2 | RAG 文档知识库（PDF/网页导入） | 高 |
| v1.3 | 任务队列（Celery + 异步执行） | 中 |
| v1.4 | Web UI 管理界面（Streamlit） | 低 |
| v2.0 | Agent 插件市场（动态加载工具） | 低 |

---

## 九、快速启动（预期）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env：填入 API Key，选择模型

# 3. CLI 模式启动
python main.py chat

# 4. API 服务启动
python main.py serve --port 8000
```

---

> 请审核以上架构方案，如有调整意见（模块增减、技术选型变更、命名规范等）请反馈，确认后开始代码生成。
