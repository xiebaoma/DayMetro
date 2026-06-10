# DayMetro

DayMetro 是一个 Godot 2D 日常模拟游戏 + FastAPI NPC Agent 后端原型。玩家从宿舍、地铁、公司、食堂、操场走完一天，并和有日程、记忆、关系、主动行为的 NPC 互动。

## 环境

- Python 3.9+
- Godot 4.6+

安装后端依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 启动后端

在项目根目录运行：

```bash
python3 -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8000
```

后端启动后可检查：

```bash
curl http://127.0.0.1:8000/health
```

默认存档数据库会生成在：

```text
.runtime/save.db
```

后端日志会写入：

```text
.runtime/logs/daymetro.log
```

如果要指定其他数据库路径：

```bash
DAYMETRO_DB_PATH=/tmp/daymetro-save.db python3 -m uvicorn server.main:app --reload --port 8000
```

如果要指定日志目录或日志级别：

```bash
DAYMETRO_LOG_DIR=/tmp/daymetro-logs DAYMETRO_LOG_LEVEL=DEBUG python3 -m uvicorn server.main:app --reload --port 8000
```

## 启动前端

后端保持运行后，打开 Godot 项目：

```bash
open -a /Applications/Godot.app /Users/xiebaoma/Desktop/DayMetro/game/project.godot
```

在 Godot 中点击运行按钮，或按 `F5` 运行。主场景是：

```text
res://scenes/Dorm.tscn
```

前端默认请求：

```text
http://127.0.0.1:8000
```

## 游玩流程

当前路线：

```text
宿舍 -> 地铁 -> 公司 -> 食堂 -> 公司 -> 操场 -> 夜晚宿舍复盘
```

基本操作：

- 方向键移动
- 靠近 NPC 后按 `Enter` 打开对话
- 对话中用上下键选择选项
- 按 `Enter` 提交选项
- 按 `Esc` 关闭对话/复盘面板

## 常用接口

世界状态：

```bash
curl http://127.0.0.1:8000/world/state
```

对话选项：

```bash
curl "http://127.0.0.1:8000/dialogue/options?npc_id=roommate_a"
```

NPC 记忆：

```bash
curl "http://127.0.0.1:8000/npc/memory?npc_id=coworker_a&limit=10"
```

NPC 关系：

```bash
curl "http://127.0.0.1:8000/npc/relation?npc_id=coworker_a"
```

NPC 主动行为：

```bash
curl "http://127.0.0.1:8000/npc/proactive?location=公司&limit=1"
```

生成每日复盘：

```bash
curl -X POST http://127.0.0.1:8000/daily/review
```

## 测试

运行普通测试：

```bash
python3 -m pytest
```

DeepSeek 真实联网测试默认会跳过。需要手动开启：

```bash
RUN_DEEPSEEK_INTEGRATION=1 \
NPC_AGENT_LLM_ENABLED=1 \
NPC_AGENT_DEEPSEEK_API_KEY="你的 DeepSeek API Key" \
python3 -m pytest test/test_deepseek_integration.py -q
```

## 运行时产物

这些文件/目录是运行时产物，已在 `.gitignore` 中忽略：

- `.runtime/`
- `.pytest_cache/`
- `data/*.db`
- `game/.godot/`
- `game/.import/`

如果想清理本地运行产物：

```bash
git clean -fdX
```

这个命令只会删除已被 `.gitignore` 忽略的文件。
