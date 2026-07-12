# 机器人调度系统（Robot Dispatch System）

一个面向仓储和园区场景的机器人任务调度示例系统。项目提供机器人状态管理、任务队列、基于规则的调度决策、地图路径计算、调度日志和 Web 可视化控制台。

> 当前版本定位为可运行的 MVP：调度器采用可解释的规则评分，并使用 MySQL 保存业务数据。

## 目录

- [项目概览](#项目概览)
- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 概览](#api-概览)
- [调度规则](#调度规则)
- [测试](#测试)
- [部署建议](#部署建议)
- [持续集成](#持续集成)
- [后续规划](#后续规划)

## 项目概览

系统由 FastAPI 后端和原生 HTML/CSS/JavaScript 前端组成。后端负责认证、任务和机器人状态管理、调度决策以及数据库访问；前端由 FastAPI 直接托管，提供调度台、任务队列、机器人列表、地图节点和决策日志。

系统启动时会执行初始化种子数据，并通过后台维护任务将长时间未上报心跳的机器人标记为离线；如果离线机器人正在执行任务，任务会退回待调度队列。

## 核心功能

- 机器人创建、状态查询和心跳上报
- 任务创建、分页查询、完成和取消
- 按优先级选择待调度任务
- 根据机器人状态、电量、能力和路线距离筛选候选机器人
- 使用 Dijkstra 算法计算地图节点之间的最短路线
- 通过数据库条件更新和行锁避免同一机器人被重复分配
- 记录每次调度的候选机器人、评分明细和决策原因
- Cookie 会话认证、生产环境配置校验和登录失败限流
- Web 调度台、任务分页、状态筛选、地图和调度日志展示
- Alembic 数据库迁移和 MySQL 并发测试

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Python 3.12、FastAPI、Uvicorn |
| 数据访问 | SQLAlchemy 2、PyMySQL |
| 数据库 | MySQL 8.4 |
| 迁移 | Alembic |
| 前端 | HTML、CSS、原生 JavaScript |
| 测试 | Python `unittest`、SQLite 单元测试、MySQL 并发测试 |

## 项目结构

```text
Robot_Dispatch_System/
├── backend/
│   ├── auth.py          # 会话认证和登录失败限流
│   ├── database.py      # 数据库连接和 Session
│   ├── dispatch.py      # 路径计算、评分和任务分配
│   ├── main.py          # FastAPI 应用和 API 路由
│   ├── models.py        # SQLAlchemy 数据模型
│   ├── schemas.py       # Pydantic 请求/响应模型
│   ├── seed.py          # 初始地图和机器人数据
│   └── time_utils.py    # UTC 时间工具
├── frontend/
│   ├── index.html       # 调度台页面
│   ├── app.js           # 前端状态和 API 交互
│   └── styles.css       # 页面样式
├── migrations/
│   └── versions/        # Alembic 迁移脚本
├── tests/               # 单元测试和 MySQL 集成测试
├── work/                # 本地辅助脚本
│   └── reset_demo.py    # 重置演示数据
├── .github/workflows/   # GitHub Actions CI
├── Dockerfile           # 后端容器镜像
├── docker-compose.yml   # MySQL 和后端服务
├── alembic.ini          # Alembic 配置
├── requirements.txt     # Python 依赖
└── .env.example         # 环境变量模板
```

## 快速开始

### 1. 一键启动完整 Demo

推荐使用 Docker 启动 MySQL 和后端服务：

```bash
docker compose up --build
```

启动后访问：http://127.0.0.1:8000

如果启动失败，优先检查 MySQL 容器是否健康、`DATABASE_URL` 是否正确，以及数据库是否已执行 `alembic upgrade head`。

停止服务：

```bash
docker compose down
```

清空 Demo 数据卷并重新初始化：

```bash
docker compose down -v
docker compose up --build
```

如果只需要重置现有数据库中的演示数据，不删除 MySQL 数据卷：

```bash
python work/reset_demo.py
```

### 2. 单独启动 MySQL

如果需要本地运行 Python 后端，也可以只启动数据库：

```bash
docker compose up -d mysql
```

### 3. 创建 Python 环境并安装依赖

Windows：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置环境变量

Windows：

```bash
copy .env.example .env
```

macOS/Linux：

```bash
cp .env.example .env
```

本地开发可以使用模板中的默认值；生产环境必须替换管理员密码和会话密钥。

### 5. 执行数据库迁移

新数据库：

```bash
alembic upgrade head
```

已有由早期版本创建的数据库：

```bash
alembic stamp 0001
alembic upgrade head
```

### 6. 启动应用

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：

- 调度台：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

默认开发账号由 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 控制，建议首次启动前修改 `.env`。

## 配置说明

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | MySQL 连接地址 | `mysql+pymysql://dispatch:dispatch@127.0.0.1:3306/robot_dispatch?charset=utf8mb4` |
| `MYSQL_ROOT_PASSWORD` | Docker MySQL root 密码 | `root` |
| `MYSQL_DATABASE` | Docker 初始化数据库名 | `robot_dispatch` |
| `MYSQL_USER` | Docker 初始化数据库用户 | `dispatch` |
| `MYSQL_PASSWORD` | Docker 初始化数据库密码 | `dispatch` |
| `MYSQL_PORT` | Docker 映射到宿主机的端口 | `3306` |
| `APP_PORT` | Docker 映射后端服务的宿主机端口 | `8000` |
| `DISPATCH_BATTERY_THRESHOLD` | 参与调度的最低电量 | `25` |
| `HEARTBEAT_OFFLINE_SECONDS` | 心跳超时秒数 | `3600` |
| `CORS_ALLOW_ORIGINS` | 允许跨域访问的前端来源，逗号分隔 | 本地两个来源 |
| `ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 管理员密码 | `change-me` |
| `SESSION_SECRET` | 会话签名密钥，生产环境至少 32 个字符 | `change-this-session-secret` |
| `SESSION_SECONDS` | 会话有效期 | `28800` |
| `COOKIE_SECURE` | HTTPS 环境是否只通过安全 Cookie 传输 | `false` |
| `SESSION_COOKIE_SAMESITE` | Cookie 跨站策略，可选 `strict`、`lax`、`none` | `strict` |
| `MAINTENANCE_INTERVAL_SECONDS` | 离线机器人检查间隔 | `30` |
| `LOGIN_WINDOW_SECONDS` | 登录失败限流窗口 | `60` |
| `LOGIN_MAX_FAILURES` | 单个客户端窗口内允许的最大失败次数 | `5` |
| `APP_ENV` | 生产环境设为 `production` | `development` |

跨域部署时，前端请求会携带 Cookie，因此 `CORS_ALLOW_ORIGINS` 必须配置为明确的前端来源，不能使用通配来源。只有在确实需要跨站 Cookie 时才使用 `SESSION_COOKIE_SAMESITE=none`，并同时启用 `COOKIE_SECURE=true` 和 HTTPS。

## API 概览

除健康检查和认证接口外，业务接口需要先登录并携带会话 Cookie。

### 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/auth/login` | 登录并创建会话 |
| `GET` | `/api/auth/session` | 查询当前会话 |
| `POST` | `/api/auth/logout` | 注销会话 |

### 机器人和任务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/robots` | 查询机器人列表 |
| `POST` | `/api/robots` | 创建机器人 |
| `POST` | `/api/robots/{robot_id}/heartbeat` | 上报机器人心跳 |
| `GET` | `/api/summary` | 查询仪表盘汇总 |
| `GET` | `/api/tasks` | 分页查询任务，可按状态筛选 |
| `POST` | `/api/tasks` | 创建任务 |
| `POST` | `/api/tasks/{task_id}/complete` | 完成任务 |
| `POST` | `/api/tasks/{task_id}/cancel` | 取消任务 |

### 调度和地图

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/dispatch/run` | 执行一次任务分配 |
| `POST` | `/api/dispatch/suggest/{task_id}` | 获取指定任务的调度建议 |
| `GET` | `/api/dispatch/logs` | 查询调度决策日志 |
| `GET` | `/api/map/nodes` | 查询地图节点 |
| `GET` | `/api/map/edges` | 查询启用的地图边 |

## 调度规则

当前版本使用可解释的固定权重评分：

```text
score = 接近任务起点的距离 × 0.55
      + 任务路线距离 × 0.25
      + 电量成本 × 0.12
```

候选机器人必须同时满足：

- 状态为 `idle`
- 电量不低于 `DISPATCH_BATTERY_THRESHOLD`
- 能力包含任务类型
- 任务起点和终点之间存在可用路线

调度器会先按优先级降序、创建时间升序选择任务，再按评分升序选择机器人。机器人状态更新采用条件更新；任务和机器人状态在同一事务中提交。

## 测试

运行全部单元测试和 API 测试：

```bash
python -m unittest discover -v
```

运行 MySQL 并发测试：

```bash
set TEST_DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/robot_dispatch_test
python -m unittest tests.test_mysql_integration -v
```

如果没有设置 `TEST_DATABASE_URL`，MySQL 并发测试会自动跳过。提交前建议至少执行：

```bash
python -m compileall -q backend migrations tests work
python -m unittest discover -v
```

## 部署建议

- 生产环境使用独立的 MySQL 用户，不要使用示例密码。
- 设置 `APP_ENV=production`、长度不少于 32 位的 `SESSION_SECRET` 和 `COOKIE_SECURE=true`。
- 仅允许可信前端来源访问，严格配置 `CORS_ALLOW_ORIGINS`。
- 使用反向代理提供 HTTPS，并关闭 `--reload`。
- 多进程或多实例部署时，应将登录限流从进程内存迁移到 Redis 等共享存储。
- 生产部署前执行迁移和 MySQL 并发测试，并配置数据库备份。

## 持续集成

仓库包含 GitHub Actions 工作流，会在 `main` 推送和 Pull Request 中自动执行：

- Docker Compose 配置检查
- MySQL 服务启动和 Alembic 迁移
- 单元测试和 MySQL 并发测试
- 前端 JavaScript 语法检查

## 后续规划

- 将登录限流和会话状态迁移到共享存储
- 引入多用户、角色和权限管理
- 增加任务失败、暂停、重试和执行历史
- 将机器人能力从逗号分隔字段拆分为关联表
- 支持可配置调度策略和更丰富的任务约束
- 增加 API 集成测试、CI 和部署检查
- 接入真实机器人遥测和路径规划服务

## License

当前仓库未声明开源许可证。如需对外发布，建议补充 `LICENSE` 文件并明确使用条款。
