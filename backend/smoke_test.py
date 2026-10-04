"""端到端冒烟测试：使用 TestClient 覆盖全部关键业务规则。

运行：DATA_DIR 指向临时目录后，python smoke_test.py
"""
import io
import os
import shutil
import struct
import sys
import tempfile
import wave

# 隔离数据目录
TEST_DIR = tempfile.mkdtemp(prefix="wb-test-")
os.environ["DATA_DIR"] = TEST_DIR
os.environ["STATIC_DIR"] = os.path.join(tempfile.gettempdir(), "wb-nonexistent-static")

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# with 块触发 lifespan（建表初始化）
client_cm = TestClient(app)
client = client_cm.__enter__()

passed = []
failed = []


def check(name, cond, detail=""):
    if cond:
        passed.append(name)
        print(f"  ✓ {name}")
    else:
        failed.append((name, detail))
        print(f"  ✗ {name} :: {detail}")


def make_wav(seconds=2.0, rate=8000):
    buf = io.BytesIO()
    frames = int(seconds * rate)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * frames)
    buf.seek(0)
    return buf


# ---------- 1. 健康检查 & 初始化 ----------
print("== 初始化与健康检查 ==")
r = client.get("/api/health")
check("health 200", r.status_code == 200, r.text)
check("数据目录已创建", os.path.isdir(os.path.join(TEST_DIR, "audio")))
check("数据库文件已创建", os.path.isfile(os.path.join(TEST_DIR, "workbench.db")))

# ---------- 2. 上传失败场景 ----------
print("== 上传校验（失败必须无半成品）==")
r = client.post("/api/audios", files={"file": ("note.txt", b"hello", "text/plain")})
check("拒绝非 MP3/WAV", r.status_code == 400, r.text)

r = client.post("/api/audios", files={"file": ("empty.mp3", b"", "audio/mpeg")})
check("拒绝空文件", r.status_code == 400, r.text)

r = client.post("/api/audios", files={"file": ("bad.wav", b"NOTANAUDIO", "audio/wav")})
check("拒绝损坏音频", r.status_code == 400, r.text)

r = client.get("/api/audios")
check("失败后音频列表仍为空（无半成品）", r.json() == [], r.text)
audio_files = os.listdir(os.path.join(TEST_DIR, "audio"))
check("临时文件已清理", audio_files == [], str(audio_files))

# 非法逐字稿编码
bad_utf16 = "中文".encode("utf-16")
r = client.post(
    "/api/audios",
    files={
        "file": ("a.wav", make_wav(2), "audio/wav"),
        "transcript_file": ("t.txt", bad_utf16, "text/plain"),
    },
)
check("拒绝非 UTF-8 逐字稿", r.status_code == 400, r.text)

# ---------- 3. 正常上传（含逐字稿）----------
print("== 正常上传 ==")
r = client.post(
    "/api/audios",
    files={
        "file": ("interview-A.wav", make_wav(10), "audio/wav"),
        "transcript_file": ("g.txt", "逐字稿内容：那一年冬天……".encode(), "text/plain"),
    },
)
check("上传带逐字稿的 WAV", r.status_code == 201, r.text)
audio_a = r.json()
check("时长被解析（约10秒）", abs(audio_a["duration"] - 10.0) < 0.5, str(audio_a))
check("逐字稿已存", r.json()["transcript_text"] == "逐字稿内容：那一年冬天……")

r = client.post("/api/audios", files={"file": ("interview-B.wav", make_wav(8), "audio/wav")})
check("上传第二个 WAV", r.status_code == 201, r.text)
audio_b = r.json()

# ---------- 4. 音频流 Range ----------
print("== 音频流式播放与 Range ==")
r = client.get(f"/api/audios/{audio_a['id']}/stream")
check("全量 200 + Accept-Ranges",
      r.status_code == 200 and r.headers.get("accept-ranges") == "bytes",
      f"{r.status_code} {dict(r.headers)}")
total = int(r.headers["content-length"])
r = client.get(f"/api/audios/{audio_a['id']}/stream", headers={"Range": "bytes=0-99"})
check("Range 返回 206", r.status_code == 206, f"{r.status_code} {r.text[:100]}")
check("分片大小正确", len(r.content) == 100, str(len(r.content)))
check("Content-Range 正确",
      r.headers.get("content-range") == f"bytes 0-99/{total}",
      r.headers.get("content-range"))
r = client.get(f"/api/audios/{audio_a['id']}/stream", headers={"Range": "bytes=99999999-"})
check("越界 Range 返回 416", r.status_code == 416, str(r.status_code))
r = client.get(f"/api/audios/9999/stream")
check("缺失音频 404", r.status_code == 404, str(r.status_code))

# ---------- 5. 事件/引文校验 ----------
print("== 事件与引文校验 ==")
r = client.post("/api/events", json={
    "title": "无引文事件", "event_date": "1938-05-01", "quotes": [],
})
check("无引文被拒", r.status_code == 400, r.text)

r = client.post("/api/events", json={
    "title": "坏引文", "event_date": "1938-05-01",
    "quotes": [{"audio_id": audio_a["id"], "start_sec": 5, "end_sec": 4}],
})
check("start>=end 被拒", r.status_code == 400, r.text)

r = client.post("/api/events", json={
    "title": "超长引文", "event_date": "1938-05-01",
    "quotes": [{"audio_id": audio_a["id"], "start_sec": 0, "end_sec": 999}],
})
check("结束秒超出时长被拒", r.status_code == 400, r.text)

r = client.post("/api/events", json={
    "title": "引用不存在音频", "event_date": "1938-05-01",
    "quotes": [{"audio_id": 99999, "start_sec": 0, "end_sec": 1}],
})
check("音频不存在被拒", r.status_code == 400, r.text)

r = client.post("/api/events", json={
    "title": "坏日期", "event_date": "1938-13-40",
    "quotes": [{"audio_id": audio_a["id"], "start_sec": 0, "end_sec": 1}],
})
check("非法日期被拒", r.status_code == 400, r.text)
check("失败后事件表为空", client.get("/api/events").json() == [])

# ---------- 6. 创建同一事件的两种说法 ----------
print("== 多说法事件 ==")
r = client.post("/api/events", json={
    "title": "1938 年文庙藏经迁移",
    "event_date": "1938-11-02",
    "description": "两位老人回忆略有出入",
    "quotes": [
        {"audio_id": audio_a["id"], "speaker": "王大爷",
         "start_sec": 1.0, "end_sec": 3.5, "quote_text": "是秋天搬走的，走水路。"},
        {"audio_id": audio_b["id"], "speaker": "李奶奶",
         "start_sec": 2.0, "end_sec": 5.0, "quote_text": "我记得是冬月里，用牛车。"},
    ],
})
check("创建两说法事件", r.status_code == 201, r.text)
event = r.json()
check("revision=1", event["revision"] == 1, str(event["revision"]))
check("entry 两引文并列", len(event["quotes"]) == 2)
check("标记为多说法（浏览端判定）", len(event["quotes"]) > 1)
event_id = event["id"]

# ---------- 7. 修订 + 乐观锁冲突 ----------
print("== 修订与并发冲突 ==")
# 甲先改成功（base_revision=1）
r = client.put(f"/api/events/{event_id}", json={
    "title": event["title"], "event_date": "1938-11-02", "description": "甲修订",
    "base_revision": 1,
    "quotes": [{"audio_id": audio_a["id"], "speaker": "王大爷",
                "start_sec": 1.0, "end_sec": 4.0, "quote_text": "甲改的文字"}],
})
check("基于 v1 修订成功 -> v2", r.status_code == 200 and r.json()["revision"] == 2, r.text)

# 乙仍拿着 v1 提交 -> 409，且携带对照数据
r = client.put(f"/api/events/{event_id}", json={
    "title": event["title"], "event_date": "1938-11-02", "description": "乙修订",
    "base_revision": 1,
    "quotes": [{"audio_id": audio_b["id"], "speaker": "李奶奶",
                "start_sec": 2.0, "end_sec": 3.0, "quote_text": "乙改的文字"}],
})
check("过期 revision 冲突 409", r.status_code == 409, r.text)
detail = r.json()["detail"]
check("冲突含服务器版本", detail.get("server_event", {}).get("revision") == 2, str(detail))
check("冲突含本人提交", detail.get("submitted", {}).get("description") == "乙修订")
check("冲突时数据保持甲的 v2",
      client.get(f"/api/events/{event_id}").json()["description"] == "甲修订")

# 乙对照后用 v2 重试 -> 成功 v3
r = client.put(f"/api/events/{event_id}", json={
    "title": event["title"], "event_date": "1938-11-02", "description": "乙覆盖重试",
    "base_revision": 2,
    "quotes": [{"audio_id": audio_b["id"], "speaker": "李奶奶",
                "start_sec": 2.0, "end_sec": 3.0, "quote_text": "乙改的文字"}],
})
check("对照后以 v2 重试成功 -> v3", r.status_code == 200 and r.json()["revision"] == 3, r.text)

# ---------- 8. 发布快照不可变 ----------
print("== 发布不可变快照 ==")
r = client.post("/api/publications", json={"note": "首版"})
check("发布 v1", r.status_code == 201 and r.json()["version"] == 1, r.text)
v1 = r.json()
check("v1 快照含 1 事件", len(v1["entries"]) == 1, str(len(v1["entries"])))
v1_quote = v1["entries"][0]["quotes"][0]
check("v1 引文=乙改的文字", v1_quote["quote_text"] == "乙改的文字", str(v1_quote))

# 发布后继续改草稿（v4），旧版引文不得变化
r = client.put(f"/api/events/{event_id}", json={
    "title": event["title"], "event_date": "1938-11-03", "description": "发布后再改",
    "base_revision": 3,
    "quotes": [{"audio_id": audio_a["id"], "speaker": "王大爷",
                "start_sec": 0.5, "end_sec": 1.5, "quote_text": "发布后新改的引文"}],
})
check("发布后草稿可继续修订 -> v4", r.status_code == 200, r.text)

r = client.get(f"/api/publications/{v1['id']}")
v1_again = r.json()
check("旧版描述不变", v1_again["entries"][0]["event_description"] == "乙覆盖重试",
      str(v1_again["entries"][0]))
check("旧版引文文字不变",
      v1_again["entries"][0]["quotes"][0]["quote_text"] == "乙改的文字",
      str(v1_again["entries"][0]["quotes"][0]))
check("旧版日期不变", v1_again["entries"][0]["event_date"] == "1938-11-02")
check("旧版记录修订号 v3", v1_again["entries"][0]["event_revision"] == 3)

# 再发布 v2，版本号递增
r = client.post("/api/publications", json={"note": ""})
check("发布 v2 版本号递增", r.status_code == 201 and r.json()["version"] == 2, r.text)
v2 = r.json()
check("v2 快照反映新引文",
      v2["entries"][0]["quotes"][0]["quote_text"] == "发布后新改的引文")

# 空发布不可能：先删草稿（需新建一个独立事件以免影响上面的断言——这里 v2 之后删全部）
# ---------- 9. 音频删除保护 ----------
print("== 音频删除保护 ==")
r = client.delete(f"/api/audios/{audio_a['id']}")
check("发布版引用的音频不可删除(409)", r.status_code == 409, r.text)
r = client.delete(f"/api/audios/{audio_b['id']}")
check("发布版引用的音频不可删除(409)", r.status_code == 409, r.text)
check("音频仍在", len(client.get("/api/audios").json()) == 2)

# 新音频只被草稿引用：先改造草稿引文都指向新音频，再尝试删旧音频
r = client.post("/api/audios", files={"file": ("c.wav", make_wav(5), "audio/wav")})
audio_c = r.json()
cur = client.get(f"/api/events/{event_id}").json()
r = client.put(f"/api/events/{event_id}", json={
    "title": cur["title"], "event_date": cur["event_date"],
    "description": cur["description"], "base_revision": cur["revision"],
    "quotes": [{"audio_id": audio_c["id"], "speaker": "丙",
                "start_sec": 0, "end_sec": 2, "quote_text": "新音频引文"}],
})
check("草稿引文改指新音频", r.status_code == 200, r.text)
# audio_a 仍被 v1/v2 快照引用 -> 仍不可删
r = client.delete(f"/api/audios/{audio_a['id']}")
check("旧音频仍被历史发布版引用，不可删", r.status_code == 409, r.text)
# audio_c 只被草稿引用 -> 也拦截
r = client.delete(f"/api/audios/{audio_c['id']}")
check("草稿引用的音频同样拦截并提示", r.status_code == 409 and "草稿" in r.json()["detail"], r.text)

# 草稿事件删除后，未发布音频可删；构造一个仅草稿引用的场景：
# 新建事件引用 c，再删该事件，c 即可删除
r = client.post("/api/events", json={
    "title": "临时事件", "event_date": "1940-01-01",
    "quotes": [{"audio_id": audio_c["id"], "start_sec": 0, "end_sec": 1,
                "quote_text": "x"}],
})
tmp_event = r.json()
# 把主事件引文从 c 挪到不影响发布引用的……直接删除两个草稿事件后 c 无引用
r = client.delete(f"/api/events/{event_id}")
check("删除草稿事件 204", r.status_code == 204, r.text)
r = client.delete(f"/api/events/{tmp_event['id']}")
check("删除临时草稿事件", r.status_code == 204, r.text)
r = client.delete(f"/api/audios/{audio_c['id']}")
check("无任何引用的音频可删除", r.status_code == 204, r.text)
files_after = os.listdir(os.path.join(TEST_DIR, "audio"))
check("删除音频时物理文件一并移除",
      all(not f.startswith(str(audio_c["id"])) for f in files_after))

# 发布版依然完整（快照独立于草稿删除）
r = client.get(f"/api/publications/{v1['id']}")
check("草稿删除后发布版仍完整", r.status_code == 200 and len(r.json()["entries"]) == 1, r.text)

# 无草稿时发布应报错
r = client.post("/api/publications", json={})
check("无草稿时发布报错", r.status_code == 400, r.text)

# ---------- 汇总 ----------
print(f"\n==== 通过 {len(passed)} 项，失败 {len(failed)} 项 ====")
shutil.rmtree(TEST_DIR, ignore_errors=True)
client_cm.__exit__(None, None, None)
sys.exit(1 if failed else 0)
