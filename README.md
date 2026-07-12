# AI Robot Dispatch System

一个最小可用的机器人调度系统示例，包含 FastAPI 后端、MySQL 数据库、基础调度规则和前端展示页。

## 功能

- 机器人状态管理和心跳接口
- 任务创建、完成、状态流转
- 任务取消与离线机器人任务自动回收
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

首次部署先执行数据库迁移：

```bash
alembic upgrade head
```

已有旧版本数据库先标记基础版本，再应用约束迁移：

```bash
alembic stamp 0001
alembic upgrade head
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
- `GET /api/summary`
- `POST /api/robots`
- `POST /api/robots/{robot_id}/heartbeat`
- `GET /api/tasks`
- `POST /api/tasks`
- `POST /api/tasks/{task_id}/complete`
- `POST /api/tasks/{task_id}/cancel`
- `POST /api/dispatch/run`
- `POST /api/dispatch/suggest/{task_id}`
- `GET /api/dispatch/logs`
- `GET /api/map/nodes`
- `GET /api/map/edges`

## 配置

- `DATABASE_URL`：MySQL 连接地址
- `DISPATCH_BATTERY_THRESHOLD`：可参与调度的最低电量
- `HEARTBEAT_OFFLINE_SECONDS`：心跳超时秒数；刷新机器人列表或运行调度时，执行中任务会退回队列
- `CORS_ALLOW_ORIGINS`：允许跨域访问的来源，多个来源使用逗号分隔
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`：调度台管理员账号
- `SESSION_SECRET`：会话签名密钥，生产环境至少 32 个字符
- `COOKIE_SECURE`：HTTPS 部署时设为 `true`
- `APP_ENV`：生产环境设为 `production`，启动时会拒绝不安全的默认认证配置
- `MAINTENANCE_INTERVAL_SECONDS`：离线机器人后台检查间隔
- `LOGIN_WINDOW_SECONDS`：登录失败限流窗口，默认 60 秒
- `LOGIN_MAX_FAILURES`：单个客户端在限流窗口内允许的最大失败次数，默认 5 次

## 测试

```bash
python -m unittest discover -v
```

使用专用 MySQL 测试库运行真实并发测试：

```bash
set TEST_DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/robot_dispatch_test
python -m unittest tests.test_mysql_integration -v
```

MySQL 并发测试需要先设置 `TEST_DATABASE_URL`，否则该测试会自动跳过。前后端跨域部署时，`CORS_ALLOW_ORIGINS` 必须配置为明确的前端来源，系统会使用带凭证的 Cookie 会话。

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
