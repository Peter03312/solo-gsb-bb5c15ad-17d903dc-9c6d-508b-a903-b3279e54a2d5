# 地方博物馆 · 口述史编年工作台

面向地方博物馆的口述史整理工具：上传采访音频与逐字稿，把录音中的说法与事件日期对应成**引文**，同一事件的多种说法并列呈现，读者可从引文一键跳转原音；草稿可反复修订，发布后生成**不可变编年版本**。

技术栈：**React 18 + Vite（前端） · FastAPI（后端） · SQLite（数据库） · 本地文件存储（音频/逐字稿）**，单容器、一键启动。

## 功能

| 需求 | 实现 |
| --- | --- |
| 上传 MP3/WAV 与逐字稿 | 音频 + `.txt` 逐字稿文件或直接粘贴文本；服务端解析时长，上传全过程原子化，失败不留半成品 |
| 填写事件日期、按音频起止秒选取引文 | 事件标题/日期/说明 + 多条引文（音频、讲述人、起止秒、引文文字），起止秒前后端双重校验，不得超出音频时长 |
| 同一事件多种说法并列 | 一个事件下任意多条引文，浏览页以并列卡片展示 |
| 引文跳原音 | 点击引文按钮，底部播放器加载对应音频并**自动 seek 到起始秒**（HTTP Range 流式播放） |
| 草稿修订 | 事件可反复编辑，修订号 `revision` 递增 |
| 发布不可变版本 | 发布时把全部事件与引文整体快照；之后改稿不影响旧版引文 |
| 并发冲突提示与对照重试 | 乐观锁（`revision`），冲突返回 409，弹窗左右对照「服务器最新版 / 我的提交」，可放弃或覆盖重试 |
| 发布版引用的音频不可删除 | 音频被发布版引用时删除返回 409；草稿引用时同样拦截并提示具体事件 |
| 无效起止秒/音频缺失/上传失败报错 | 统一 400/404/409 错误提示；上传先写 `.part` 临时文件、成功后才落库落盘，失败自动清理 |
| 编辑、发布、浏览 Web 页面 | 顶部四个页签：编年浏览 / 事件草稿 / 音频库 / 发布 |

## 一键启动（Docker Compose）

需要 Docker 与 Docker Compose 插件：

```bash
docker compose up -d --build
```

启动后访问：

- **应用地址**：http://localhost:8000
- **健康检查**：http://localhost:8000/api/health
- 首次启动自动在 `./data` 下创建 SQLite 数据库（`workbench.db`）、`audio/`、`transcripts/` 目录并完成建表初始化，无需任何手动步骤。

停止：

```bash
docker compose down       # 停止，数据保留在 ./data
docker compose down -v    # 注意：本项目的卷是绑定挂载，加 -v 不会删除 ./data
```

## 配置

通过环境变量配置（见 `docker-compose.yml`）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATA_DIR` | `/data` | 数据根目录（SQLite + 上传文件），容器内已挂载到宿主机 `./data` |
| `MAX_AUDIO_BYTES` | `209715200`（200MB） | 单个音频大小上限 |
| `MAX_TRANSCRIPT_BYTES` | `5242880`（5MB） | 逐字稿大小上限，仅接受 UTF-8 文本 |
| `STATIC_DIR` | `/app/static` | 前端构建产物目录，通常无需修改 |

端口修改：编辑 `docker-compose.yml` 的 `ports`，例如 `"9000:8000"` 后通过 http://localhost:9000 访问。

备份：直接复制整个 `./data` 目录即可（建议在停止或无写入时备份）。

## 本地开发（不用 Docker）

后端（Python 3.11+）：

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATA_DIR=./../data uvicorn app.main:app --reload --port 8000
```

前端（Node 20+）：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 ，/api 自动代理到 8000
```

前端生产构建：`npm run build`（产物在 `frontend/dist`，可用 `STATIC_DIR` 指给 FastAPI 托管）。

## 使用流程

1. **音频库**：上传采访录音（MP3/WAV），可一并上传或粘贴逐字稿。
2. **事件草稿**：新建事件，填写事件日期与说明；为每种说法添加一条引文，选择来源音频并填写起止秒，可「从起始秒试听」核对。
3. **发布**：核对无误后发布，生成 `v1、v2 ……` 不可变版本。
4. **编年浏览**：选择历史发布版查看固化内容，或查看当前草稿；点击引文中的「跳转原音」回听原始录音片段。
5. 修订旧事件时如他人已先保存，会弹出冲突对照窗口，按提示重试即可。

## 目录结构

```
backend/            FastAPI 应用
  app/
    main.py         入口 + 静态托管 + SPA 回退
    config.py       路径/上限配置
    database.py     SQLite 连接、WAL、建表初始化
    schemas.py      请求模型
    routers/        events / audios / publications
frontend/           React + Vite 单页应用
  src/
    pages/          浏览、草稿、音频库、发布四个页面
    components/     事件编辑器、冲突对照弹窗、全局播放器
Dockerfile          多阶段构建（前端构建 -> 后端运行时）
docker-compose.yml  一键启动 + 数据卷持久化
```
