我建议 DayMetro 不要做成“真实物理城市模拟”，而是做成：

2D / 2.5D 城市日常模拟 + Agent NPC 社交系统

也就是：玩家在宿舍、地铁、公司、食堂、操场这些场景里移动；NPC 有自己的日程、情绪、记忆、关系和目标；玩家可以和他们聊天、帮忙、冲突、建立关系。核心卖点不是物理，而是“城市里的 NPC 像真实的人”。

我推荐的技术选型
1. 游戏引擎：Godot 4

优先选 Godot 4 + 2D/伪 3D。

原因很简单：

Godot 免费开源，适合小团队或个人项目；它原生支持 2D/3D 游戏开发，并且有 NavigationAgent2D / NavigationAgent3D 这种现成导航组件，可以帮 NPC 做寻路、避障、移动，不需要你自己写复杂物理和路径规划。Godot 文档里也明确提到 NavigationAgent 可以做路径查找、路径跟随和 agent avoidance。

DayMetro 这种项目没必要一上来用 Unity。 Unity 的 NavMeshAgent 也很成熟，能让 NPC 基于 NavMesh 移动和避障。 但 Unity 工程更重，C#、资源管理、构建流程、包管理都会让你把精力分散到“做游戏工业流程”上，而不是 Agent NPC。

所以我会选：

Godot 4
+ 2D 俯视角 / 等距视角
+ TileMap 搭场景
+ NavigationAgent2D 做 NPC 移动
+ Area2D 做交互触发

不要做复杂碰撞，不要做真实地铁系统，不要做城市交通仿真。

推荐架构
Godot 客户端
  ├── 场景渲染：宿舍 / 地铁 / 公司 / 食堂 / 操场
  ├── 玩家控制：移动、点击、对话、选择行为
  ├── NPC 表现：移动、说话气泡、表情、动画
  └── 本地事件系统：进入区域、靠近 NPC、触发剧情

Python Agent 后端
  ├── NPC 大脑：日程、目标、情绪、记忆、关系
  ├── 对话系统：LLM / 规则 / 模板混合
  ├── 行为决策：今天去哪、和谁说话、做什么
  ├── 记忆系统：短期记忆 + 长期记忆
  └── 存档系统：SQLite / JSON

通信
  └── Godot HTTP / WebSocket 调用 Python 后端

这个架构的好处是：游戏引擎只负责表现，Agent 系统独立开发。以后你甚至可以把 Agent 后端单独拿出来，包装成一个“虚拟城市 NPC 大脑系统”。

NPC Agent 怎么实现比较合适？

不要一开始就搞很复杂的多 Agent 框架。可以分三层。

第一层：规则驱动 NPC

先给每个 NPC 一个固定日程。

{
  "name": "张昊",
  "role": "室友",
  "personality": "外向、爱打游戏、嘴硬心软",
  "schedule": [
    {"time": "07:00", "action": "起床", "location": "宿舍"},
    {"time": "08:00", "action": "去上课", "location": "教学楼"},
    {"time": "20:00", "action": "回宿舍打游戏", "location": "宿舍"}
  ]
}

这个阶段 NPC 看起来已经“活”了：

早上在宿舍
中午在食堂
晚上在操场或宿舍
玩家靠近就能互动

这一步最重要，因为它保证游戏不是空的。

第二层：状态机 + 轻量 Agent

每个 NPC 有几个核心状态：

当前地点 location
当前行为 action
当前心情 mood
当前目标 goal
和玩家关系 relation
记忆 memory

比如：

{
  "mood": "疲惫",
  "goal": "完成今天的实习日报",
  "relation_with_player": 35,
  "memory": [
    "玩家昨天答应一起吃晚饭但爽约了",
    "玩家最近在准备面试"
  ]
}

然后 NPC 的行为不是完全随机，而是由状态决定：

如果 mood = 疲惫：
    更可能拒绝长时间聊天

如果 relation_with_player > 60：
    会主动分享秘密或邀请玩家

如果玩家连续几天不互动：
    关系下降

如果 NPC 记得玩家上次帮过他：
    下次对话会提到这件事

这就是 DayMetro 的核心体验：NPC 不是任务发布器，而是有记忆的人。

第三层：LLM 对话

LLM 不要控制所有东西。它只负责生成“自然语言”。

也就是说，NPC 的行为逻辑最好还是你自己控制：

规则系统决定：
    NPC 此刻愿不愿意聊天
    NPC 知不知道某件事
    NPC 对玩家态度如何
    NPC 是否触发任务

LLM 负责：
    把这些状态转换成自然对话

比如给 LLM 的 prompt 可以是：

你是张昊，玩家的大学室友。
你的性格：外向、爱打游戏、嘴硬心软。
你当前心情：有点困。
你和玩家关系：不错。
你记得：玩家昨天晚上在宿舍学到了很晚。
当前场景：早上 7 点，宿舍。
玩家说：“早啊，今天有课吗？”

请用自然、口语化的方式回复，不要超过 30 字。

输出：

早啊，我上午有一节课。你昨晚学那么晚，今天顶得住吗？

这种感觉就出来了。

Agent 框架要不要用 LangGraph？

可以用，但不是第一阶段必须。

LangGraph 的定位是构建 stateful、long-running agent workflow，也就是有状态、可持续运行的 Agent 工作流。它适合做复杂 NPC 行为链，比如“感知事件 → 更新记忆 → 判断情绪 → 决定行为 → 生成对话 → 写回状态”。

但 DayMetro 初期不要直接上很复杂的多 Agent 系统。我的建议是：

MVP 阶段：
    Python 自己写 NPCAgent 类

进阶阶段：
    再用 LangGraph 管 NPC 决策流程

比如后期可以变成：

玩家输入
  ↓
感知节点 Perception
  ↓
记忆检索 Memory Retrieval
  ↓
情绪更新 Emotion Update
  ↓
行为决策 Action Decision
  ↓
对话生成 Dialogue Generation
  ↓
状态写回 State Update

LangGraph 对这种图式工作流比较合适，而且它也有 multi-agent workflow 的设计思路。

物理场景怎么简化？

DayMetro 不应该做真实物理模拟，而是做“可交互场景”。

场景只需要这些东西
1. 地图
2. 可走区域
3. 交互点
4. NPC
5. 时间系统
6. 事件触发器

比如公司场景：

工位区：可以工作
会议室：10 点早会
电梯口：上下楼
食堂入口：12 点触发吃饭事件
同事 NPC：可聊天
老板 NPC：触发任务

你不需要模拟：

真实地铁运行
真实人群碰撞
真实城市交通
真实工作流程
真实经济系统

只需要做到：

玩家感觉“我在城市里过了一天”
NPC 感觉“他们有自己的生活”
玩家如何和 NPC 交互？

我建议做四种交互。

1. 普通聊天

玩家靠近 NPC，按 E 进入聊天。

玩家：今天早会讲啥？
同事：还是那个项目进度呗，不过老板好像挺急的。

这是最基础的交互。

2. 选项式行为

不要让玩家只能自由输入。最好保留选项。

A. 问他今天忙不忙
B. 邀请他一起吃饭
C. 吐槽早会
D. 结束对话

选项影响 NPC 状态：

邀请吃饭成功：关系 +5
吐槽早会：如果 NPC 也讨厌早会，关系 +3
如果 NPC 是卷王，关系 -2

这样比纯 LLM 对话更容易做成游戏。

3. 自由输入对话

进阶一点，可以允许玩家输入一句话。

玩家：我今天有点累，不想上班。
NPC：哈哈谁不是呢，要不午休多睡会儿？

但自由输入要受状态约束。NPC 不能随便答应所有事情。

例如玩家说：

你能不能帮我把老板打一顿？

NPC 不应该真的执行，而是根据性格拒绝：

你电视剧看多了吧，我最多帮你吐槽两句。
4. 关系与记忆反馈

这是最重要的。

NPC 要记住玩家做过的事。

玩家昨天帮同事改 bug
今天同事主动请玩家吃饭

玩家连续三天没理室友
室友说：你最近咋都不跟我们玩了？

这会让玩家觉得 NPC 是连续存在的，而不是每次对话都重置。

数据库选型

MVP 用 SQLite 就够了。

npc表
npc_memory表
player_relation表
event_log表
save_state表

比如：

npc(id, name, personality, current_location, mood, goal)

npc_memory(id, npc_id, content, importance, created_at)

player_relation(npc_id, relation_score, trust_score, conflict_score)

event_log(id, event_type, actor, target, content, time)

后期如果你想展示技术深度，可以再加：

向量数据库 / 本地 embedding 检索

用于 NPC 长期记忆检索：

玩家问：“你还记得我上次说的面试吗？”
系统从 memory 里检索相关记忆
再交给 LLM 生成回答

但 MVP 阶段先别上向量库，直接 SQLite + keyword 检索都行。

最适合你的最终技术栈

我觉得你可以这样选：

客户端：
    Godot 4
    GDScript
    2D / 等距视角
    TileMap + NavigationAgent2D

后端：
    Python
    FastAPI
    SQLite
    可选 LangGraph

LLM：
    开发期用 OpenAI / Claude / Gemini API
    后期可适配本地模型

通信：
    HTTP：普通对话请求
    WebSocket：实时 NPC 状态推送，可后期再做

存档：
    SQLite + JSON

项目结构可以是：

DayMetro/
  game/
    scenes/
    scripts/
    assets/
  server/
    main.py
    npc_agent.py
    memory.py
    dialogue.py
    scheduler.py
    database.py
  data/
    npcs.json
    locations.json
    schedules.json
    save.db
MVP 版本应该做什么？

第一版不要做“大城市”。只做一个完整日循环：

宿舍 → 地铁 → 公司 → 食堂 → 公司 → 学校操场 → 宿舍

NPC 只需要 5 个：

1. 室友A：爱打游戏
2. 室友B：卷王
3. 同事A：友善
4. 同事B：爱吐槽
5. 老板/导师：任务压力来源

系统只做 5 个核心能力：

1. 时间流逝
2. NPC 按日程移动
3. 玩家靠近 NPC 可对话
4. NPC 有关系值和记忆
5. 玩家选择会影响后续对话

这就已经是一个很完整的原型了。

我最推荐的路线
第一阶段：Godot 单机 Demo
    做地图、移动、NPC、对话框、时间系统

第二阶段：接 Python 后端
    NPC 状态、日程、关系、记忆放到后端

第三阶段：接 LLM
    让 NPC 能自然聊天，但行为仍由规则控制

第四阶段：加入记忆系统
    NPC 记住玩家做过的事

第五阶段：加入 Agent 决策
    NPC 不只是聊天，而是会主动行动

一句话总结：

DayMetro 的技术重点不应该是物理模拟，而应该是“NPC 状态机 + 记忆系统 + LLM 对话 + 日程驱动行为”。

所以我最推荐：

Godot 4 + Python FastAPI + SQLite + 规则 Agent + 可选 LangGraph + LLM API

这个技术栈简单、可控、能做出效果，而且很适合你后续往“Agent NPC 系统”这个方向深入。