# AI Robot Dispatch System

一个最小可用的机器人调度系统示例，包含 FastAPI 后端、MySQL 数据库、基础调度规则和前端展示页。

## 功能

- 机器人状态管理和心跳接口
- 任务创建、完成、状态流转
- 基于规则评分的 AI 调度建议
- 自动选择优先级最高的待调度任务
- 调度决策日志
- 地图节点展示
- FastAPI 直接托管前端展示页

## 本地启动

1. 启动 MySQL：

```bash
docker compose up -d mysql
```

2. 安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境变量：

```bash
copy .env.example .env
```

4. 启动后端和展示页：

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

访问：

- 展示页：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

## 核心接口

- `GET /api/robots`
- `POST /api/robots`
- `POST /api/robots/{robot_id}/heartbeat`
- `GET /api/tasks`
- `POST /api/tasks`
- `POST /api/tasks/{task_id}/complete`
- `POST /api/dispatch/run`
- `POST /api/dispatch/suggest/{task_id}`
- `GET /api/dispatch/logs`
- `GET /api/map/nodes`

## 调度规则

第一版采用可解释的规则评分：

```text
score = 到任务起点距离 * 0.55
      + 任务路线距离 * 0.25
      + 电量成本 * 0.12
      - 任务优先级奖励
```

候选机器人必须满足：

- 状态为 `idle`
- 电量不低于阈值，默认 25%
- 能力包含任务类型

后续可以把 `backend/dispatch.py` 中的评分逻辑替换为预测模型或策略服务。
