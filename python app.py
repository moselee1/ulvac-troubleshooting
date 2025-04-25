import os, io, base64, sqlite3
from contextlib import closing

import pandas as pd
from flask import (
    Flask, render_template, request, redirect,
    url_for, send_file, flash
)
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ── 그래프 설정 ─────────────────────────────
import matplotlib
matplotlib.use("Agg")            # 서버‑사이드 렌더링
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# 한글 글꼴 설정 (설치된 글꼴 중 우선순위로 선택)
for font in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Nanum Gothic"]:
    if any(font in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = font
        break
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 부호 깨짐 방지

# ── 기본 설정 ──────────────────────────────
app = Flask(__name__)
app.secret_key = "ulvac‑trouble‑secret"

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=20 * 1024 * 1024        # 20 MB
)
ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}

def allowed_file(name): return os.path.splitext(name)[1].lower() in ALLOWED_EXTS

# ── 전역 임베딩 모델 ──────────────────────
try:
    EMB_MODEL = SentenceTransformer("paraphrase-MiniLM-L6-v2")
except Exception as e:
    EMB_MODEL = None
    print("⚠️  SentenceTransformer 로드 실패:", e)

# ── DB 유틸 ────────────────────────────────
DB = "troubleshooting.db"
def conn(): c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with closing(conn()) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS troubleshooting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trouble_date TEXT, device_code TEXT, device_name TEXT,
                user_name TEXT, trouble_text TEXT, solution TEXT,
                image TEXT, category TEXT, tags TEXT
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trouble_id INTEGER, value INTEGER
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trouble_id INTEGER, commenter_name TEXT, comment TEXT
            );
            """
        )
        c.commit()

# ── 유사도 계산 ────────────────────────────
def sims(query, rows):
    if not EMB_MODEL or not query.strip() or not rows:
        return []
    q = EMB_MODEL.encode([query])
    d = EMB_MODEL.encode([r["trouble_text"] for r in rows])
    return cosine_similarity(q, d)[0].tolist()

# ── Excel 입출력 ───────────────────────────
def export_excel():
    with closing(conn()) as c:
        df = pd.read_sql("SELECT * FROM troubleshooting", c)
    out = os.path.join("static", "troubleshooting_data.xlsx")
    df.to_excel(out, index=False)
    return out

def import_excel(fileobj):
    df = pd.read_excel(fileobj).where(pd.notnull, None)
    with closing(conn()) as c:
        for _, r in df.iterrows():
            c.execute(
                """INSERT INTO troubleshooting
                   (trouble_date, device_code, device_name, user_name,
                    trouble_text, solution, image, category, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("trouble_date"), r.get("device_code"),
                    r.get("device_name"), r.get("user_name"),
                    r.get("trouble_text"), r.get("solution"),
                    r.get("image"), r.get("category"), r.get("tags"),
                ),
            )
        c.commit()

# ── Routes ────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.form

        # 코멘트
        if "commenter_name" in f and "comment" in f:
            with closing(conn()) as c:
                c.execute(
                    "INSERT INTO comments (trouble_id, commenter_name, comment) VALUES (?, ?, ?)",
                    (f["trouble_id"], f["commenter_name"], f["comment"]),
                ); c.commit()
            return redirect(url_for("index"))

        # 검색
        if "search_query" in f:
            q = f["search_query"].strip()
            tags = [t.strip().lower() for t in f.get("search_tags", "").split(",") if t.strip()]

            with closing(conn()) as c:
                rows = c.execute("SELECT * FROM troubleshooting").fetchall()
                fb   = c.execute("SELECT trouble_id, SUM(value) AS cnt FROM feedback GROUP BY trouble_id").fetchall()
                cmts = c.execute("SELECT * FROM comments").fetchall()

            fb_map = {r["trouble_id"]: r["cnt"] for r in fb}
            cmt_map = {}
            for c in cmts:
                cmt_map.setdefault(c["trouble_id"], []).append(
                    {"commenter_name": c["commenter_name"], "comment": c["comment"]}
                )

            if tags:
                rows = [r for r in rows if any(t in (r["tags"] or "").lower().split(",") for t in tags)]

            sim = sims(q, rows) if rows else []
            res = []
            if sim:
                for r, s in sorted(zip(rows, sim), key=lambda x: x[1], reverse=True):
                    if s >= .30:
                        res.append((dict(r), s, fb_map.get(r["id"], 0), cmt_map.get(r["id"], [])))
            else:
                res = [(dict(r), 1.0, fb_map.get(r["id"], 0), cmt_map.get(r["id"], [])) for r in rows]

            return render_template("index.html", results=res, search_query=q, search_tags=",".join(tags))

        # 트러블 등록
        def image_process(entry):
            file_ = request.files.get("image")
            if file_ and file_.filename:
                if not (allowed_file(file_.filename) and file_.mimetype in {"image/png","image/jpeg"}):
                    flash("잘못된 이미지 형식입니다", "error"); return
                fname = secure_filename(f"{entry['device_code']}_{entry['trouble_date']}{os.path.splitext(file_.filename)[1].lower()}")
                file_.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                entry["image"] = fname
            elif f.get("clipboard_image_data","").startswith("data:image/"):
                head, b64 = f["clipboard_image_data"].split(",",1)
                fmt = head.split("/")[1].split(";")[0]
                if fmt not in {"png","jpeg","jpg"}:
                    flash("클립보드 이미지 형식 오류", "error"); return
                data = base64.b64decode(b64)
                if len(data) > app.config["MAX_CONTENT_LENGTH"]:
                    flash("클립보드 이미지가 20 MB를 초과", "error"); return
                ext = ".png" if fmt=="png" else ".jpg"
                fname = secure_filename(f"{entry['device_code']}_{entry['trouble_date']}{ext}")
                with open(os.path.join(app.config["UPLOAD_FOLDER"], fname),"wb") as w: w.write(data)
                entry["image"] = fname

        entry = dict(
            trouble_date = f["trouble_date"],
            device_code  = f["device_code"],
            device_name  = f["device_name"] if f["device_name_select"]=="직접입력" else f["device_name_select"],
            user_name    = f["user_name"],
            trouble_text = f["trouble_text"],
            solution     = f["solution"],
            category     = f.get("category",""),
            tags         = f.get("tags",""),
            image        = None
        )
        image_process(entry)
        with closing(conn()) as c:
            c.execute(
                """INSERT INTO troubleshooting
                   (trouble_date,device_code,device_name,user_name,
                    trouble_text,solution,image,category,tags)
                   VALUES (:trouble_date,:device_code,:device_name,:user_name,
                           :trouble_text,:solution,:image,:category,:tags)""",
                entry); c.commit()
        flash("등록 완료!", "ok")
        return redirect(url_for("index"))

    return render_template("index.html", results=None)

@app.route("/feedback/<int:tid>", methods=["POST"])
def feedback(tid):
    with closing(conn()) as c:
        c.execute("INSERT INTO feedback (trouble_id,value) VALUES (?,1)", (tid,)); c.commit()
    return redirect(url_for("index"))

# ── 통계 메인 표 ───────────────────────────
@app.route("/stats")
def stats():
    with closing(conn()) as c:
        df = pd.read_sql(
            """SELECT device_name,
                      COALESCE(category,'없음') AS category,
                      COUNT(*) AS trouble_count
               FROM troubleshooting
               GROUP BY device_name, COALESCE(category,'없음')""",
            c
        )
    return render_template("stats.html", stats=df.to_dict("records"))

# ── 장치 목록 (그래프 메뉴) ────────────────
@app.route("/stats/devices")
def stats_devices():
    with closing(conn()) as c:
        devices = [r["device_name"] for r in c.execute("SELECT DISTINCT device_name FROM troubleshooting")]
    return render_template("stats_devices.html", devices=devices)

# ── pie 그래프 ────────────────────────────
@app.route("/stats/pie/<device>")
def stats_pie(device):
    with closing(conn()) as c:
        df = pd.read_sql(
            """SELECT COALESCE(category,'없음') AS category,
                      COUNT(*) AS cnt
               FROM troubleshooting
               WHERE device_name = ?
               GROUP BY COALESCE(category,'없음')""",
            c, params=(device,)
        )
    if df.empty:
        return f"‘{device}’ 데이터가 없습니다.", 404

    fig, ax = plt.subplots()
    ax.pie(
        df["cnt"], labels=df["category"],
        autopct="%1.1f%%", startangle=140,
        wedgeprops={"linewidth":.5,"edgecolor":"white"}
    )
    ax.set_title(f"{device} 카테고리별 트러블 비율")
    ax.axis("equal")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight"); plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ── Excel 입출력 ───────────────────────────
@app.route("/export")
def export(): return send_file(export_excel(), as_attachment=True)

@app.route("/import", methods=["POST"])
def import_data():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".xlsx"):
        flash("Excel 파일을 선택하세요", "error"); return redirect(url_for("index"))
    import_excel(f); flash("업로드 완료!", "ok"); return redirect(url_for("index"))

# ── 서버 기동 ──────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

