from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn

app = FastAPI(title="AI News Archive")

@app.get("/", response_class=HTMLResponse)
def index():
    archive_dir = Path("data/archive")
    if not archive_dir.exists():
        return "<h1>Chưa có bản tin nào! Hệ thống cần chạy ít nhất 1 lần.</h1>"
        
    files = sorted(archive_dir.glob("*.html"), reverse=True)
    if not files:
        return "<h1>Chưa có bản tin nào!</h1>"
        
    links = "".join([
        f"<li style='margin-bottom: 10px;'>"
        f"<a href='/archive/{f.name}' style='color: #2563eb; text-decoration: none; font-size: 18px; font-family: sans-serif;'>"
        f"Bản tin ngày {f.stem.replace('digest_', '')}"
        f"</a></li>" 
        for f in files
    ])
    
    html = f"""
    <html>
    <head><title>AI News Archive</title></head>
    <body style="font-family: sans-serif; padding: 40px; background-color: #f3f4f6;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h1 style="color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 15px;">Kho lưu trữ AI News</h1>
            <ul style="list-style: none; padding: 0; margin-top: 20px;">
                {links}
            </ul>
        </div>
    </body>
    </html>
    """
    return html

@app.get("/archive/{filename}", response_class=HTMLResponse)
def get_archive(filename: str):
    file_path = Path("data/archive") / filename
    if not file_path.exists():
        return "<h1>Không tìm thấy bản tin!</h1>", 404
    return file_path.read_text(encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
