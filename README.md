# 地方博物馆 · 口述史编年工作台

面向地方博物馆 / 文史工作者的口述史编年（chronicle）工作台：

- 上传口述采访 **MP3 / WAV** 原音与逐字稿（**TXT / SRT / VTT**，UTF-8）；
- 为事件填写日期（`YYYY` / `YYYY-MM` / `YYYY-MM-DD`），按音频**起止秒**锚定引文；
- 同一事件的**多种说法并列**展示，读者点击引文即可**跳至原音**对应片段播放；
- 草稿可反复修订（带修订号与并发冲突对照），发布生成**不可变编年版本**；
- 后续改稿不会改变旧版引文——发布时对全部字段做深拷贝快照；
- 已被（草稿或发布版）引文引用的音频**不可删除**；
- 无效起止秒、音频缺失 / 损坏、上传失败一律报错，**不产生半成品记录或残留文件**。

技术栈：**React 18 + Vite**（前端）、**FastAPI + SQLAlchemy**（后端）、**SQLite**（数据库）、
本地文件系统（音频 / 逐字稿存储）、**HTTP Range** 音频流式播放，Docker 多阶段构建一键启动。

---

## 一、一键启动（推荐，Docker Compose）

前置：已安装 Docker Engine 20.10+ 与 Docker Compose v2（`docker compose` 命令可用）。

```bash
docker compose up -d --build
```

首次启动会：构建前后端镜像 → 创建 SQLite 数据库与数据表 → 建好音频 / 逐字稿存储目录。

访问地址：

| 用途 | 地址 |
| --- | --- |
| **Web 工作台（编辑 / 发布 / 浏览）** | **http://localhost:8000/** |
| 健康检查 | http://localhost:8000/api/health |
| OpenAPI 交互文档 | http://localhost:8000/docs |

查看日志 / 停止：

```bash
docker compose logs -f
docker compose down            # 停止（保留数据）
```

数据持久化在命名卷 `museum-data`（容器内 `/data`，包含 `museum.db`、`media/audio`、`media/transcripts`）。
彻底清空数据：`docker compose down -v`（**会删除全部录音与编年数据，谨慎执行**）。

镜像内置 **ffmpeg/ffprobe**，用于可靠探测 MP3/WAV 时长。

---

## 二、本地开发启动（不使用 Docker）

需要 Node.js ≥ 18、Python ≥ 3.11；开发机建议安装 `ffmpeg`（否则仅标准 WAV 可被解析时长）。

### 1. 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 数据目录（SQLite 与上传文件）可自定义
export DATA_DIR=./data
export STATIC_DIR=../frontend/dist   # 提供前端构建产物；开发时可指向不存在的目录
uvicorn app.main:app --reload --port 8000
```

### 2. 前端（另开终端）

```bash
cd frontend
npm install
npm run dev
```

打开 Vite 开发服务器 **http://localhost:5173/**（已配置 `/api` 反向代理到 `http://localhost:8000`）。
后端在其他地址时，用 `VITE_API_TARGET=http://其他主机:8000 npm run dev` 覆盖。

生产构建：`cd frontend && npm run build`，产物在 `frontend/dist`，由 FastAPI 直接托管。

---

## 三、使用流程

1. **音频库**：上传 MP3/WAV（可选逐字稿、讲述人）。上传时服务器完整接收临时文件并用 ffprobe
   校验可读与时长、解析逐字稿；成功后文件才原子落盘并写入数据库，任何失败都自动回滚清理。
2. **草稿编辑**：新建事件（标题、日期、地点、背景），为其添加若干引文：
   - 选择音频、填写 / 用「取当前播放点」填入起止秒，可从 SRT/VTT 自动截取该时间段文字；
   - 同一事件可添加多条引文（不同讲述人 / 不同说法），保存后在浏览页并列呈现；
   - 客户端即时校验 + 服务端强校验：结束秒必须大于开始秒、不得超出音频时长等。
3. **并发修改**：保存时携带修订号 `revision`。若他人已先行保存，返回 **409 冲突**，
   页面弹出两侧（服务器最新版 / 你的未保存改动）对照表，可选「保留我的改动」或
   「采用服务器最新版」为基础，合并后以最新修订号**重试保存**。
4. **发布管理**：给出版本名称（与说明），一键把当前全部事件与引文固化为不可变版本
   （第 1 版、第 2 版……递增）。发布串行化，两个管理员同时发布也不会产生重号。
5. **编年浏览**：左侧切换历史版本，时间线按日期排列事件；事件下多条说法并列，
   点「▶ 听原音」即从引文开始秒播放到结束秒，底部播放器显示片段区间与进度。

### 不可变性与删除规则

- 发布版本是**深拷贝快照**（`releases / event_snapshots / quote_snapshots` 三张表），
  之后修改草稿、调整引文起止秒甚至删除草稿，均不影响任何已发布版本；
- 已进入发布版本的事件草稿不可删除（接口返回 409）；
- 音频只要被任意草稿引文或发布版快照引用就不可删除（409 并告知引用数量）；
  只有未被引用的音频可删除，删除在数据库事务提交成功后才移除磁盘文件。

---

## 四、配置（环境变量）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATA_DIR` | `/data` | 数据根目录（SQLite 与媒体文件） |
| `DATABASE_URL` | `sqlite:///$DATA_DIR/museum.db` | 数据库连接串（SQLite） |
| `STATIC_DIR` | `/app/static` | 前端静态产物目录（容器内已放好） |
| `MAX_UPLOAD_MB` | `512` | 单个上传文件大小上限（MB） |
| `PORT` | `8000` | uvicorn 监听端口 |
| `WEB_CONCURRENCY` | `1` | uvicorn worker 数；多 worker 下 SQLite 写入靠 WAL + `BEGIN IMMEDIATE` 串行化，单机场景保持 1 即可 |

修改端口（宿主机映射）请编辑 `docker-compose.yml` 的 `ports`，如 `"9000:8000"` 后访问 http://localhost:9000/。

---

## 五、目录结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 入口、异常处理、SPA 托管
│   │   ├── config.py            # 配置
│   │   ├── database.py / models.py / schemas.py
│   │   ├── routers/            # media / events / releases / files(音频Range)
│   │   ├── serializers.py
│   │   └── services/           # 上传暂存原子化、ffprobe 时长、SRT/VTT 解析、引文校验
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/              # 浏览 / 草稿 / 音频库 / 发布
│   │   ├── components/         # 引文卡片、冲突对照、底部播放器
│   │   ├── player.jsx          # 全局音频播放上下文（片段起止）
│   │   └── api.js
│   └── package.json / vite.config.js
├── docker/entrypoint.sh
├── Dockerfile                  # 多阶段：Node 构建前端 → python-slim 运行
├── docker-compose.yml
└── README.md
```

## 六、主要 HTTP 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/media` | multipart 上传音频（+可选逐字稿、讲述人） |
| GET / DELETE | `/api/media/{id}` | 查看 / 删除（被引用返回 409） |
| GET | `/api/media/{id}/audio` | 音频流，支持 `Range`（206） |
| GET | `/api/media/{id}/transcript` | 逐字稿原文 |
| GET | `/api/media/{id}/quote-text?start=&end=` | 截取时间段字幕文本 |
| GET / POST | `/api/events` | 草稿列表 / 新建 |
| GET / PUT / DELETE | `/api/events/{id}` | 详情 / 更新（PUT 须带 `revision`，冲突 409 附对照） / 删除 |
| POST | `/api/releases` | 发布不可变版本 |
| GET | `/api/releases`、`/api/releases/latest`、`/api/releases/{id}` | 版本列表 / 快照详情 |
