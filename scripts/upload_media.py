"""通过后台上传接口，把 media/wallpapers 里的图片全部写入数据库。

用法：
    python scripts/upload_media.py                    # 上传 media/wallpapers 下的全部图片
    python scripts/upload_media.py --dry-run          # 只看会传多少张，不发请求
    python scripts/upload_media.py --source some/dir  # 指定别的图片目录

已成功上传的文件名会记录在 scripts/.uploaded_media.txt，重复执行会自动跳过，
想全部重传时删掉这个文件即可。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "media" / "wallpapers"
PROGRESS_FILE = ROOT / "scripts" / ".uploaded_media.txt"


def post_json(url: str, payload: dict, token: str | None = None, timeout: int = 60) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, timeout: int = 60) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def login(base_url: str, username: str, password: str) -> str:
    body = post_json(
        f"{base_url}/user/login/", {"username": username, "password": password}
    )
    if body.get("code") != 200:
        raise SystemExit(f"登录失败：{body.get('message') or body}")
    return body["token"]["access"]


def build_multipart(files: list[Path], fields: dict[str, str], boundary: str) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )
    for path in files:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="images"; '
            f'filename="{path.name}"\r\nContent-Type: {content_type}\r\n\r\n'.encode("utf-8")
        )
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def upload_batch(
    base_url: str,
    files: list[Path],
    fields: dict[str, str],
    token: str,
    credentials: tuple[str, str],
    retries: int = 3,
) -> dict:
    boundary = "----wallpaper" + uuid.uuid4().hex
    body = build_multipart(files, fields, boundary)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    last_error = ""
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            f"{base_url}/wallpapers/bulk-upload/", data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            last_error = f"HTTP {exc.code}: {detail[:300]}"
            if exc.code == 401:
                # access token 默认 5 分钟，长任务里会过期，重新登录换一个
                token = login(base_url, *credentials)
                headers["Authorization"] = f"Bearer {token}"
                continue
        except Exception as exc:  # 网络抖动等
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(2 * attempt)

    raise RuntimeError(f"上传失败（{len(files)} 张）：{last_error}")


def make_batches(files: list[Path], max_bytes: int, max_files: int) -> list[list[Path]]:
    batches: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0
    for path in files:
        size = path.stat().st_size
        if current and (current_size + size > max_bytes or len(current) >= max_files):
            batches.append(current)
            current, current_size = [], 0
        current.append(path)
        current_size += size
    if current:
        batches.append(current)
    return batches


def load_done() -> set[str]:
    if not PROGRESS_FILE.exists():
        return set()
    return {
        line.strip()
        for line in PROGRESS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def mark_done(names: list[str]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS_FILE.open("a", encoding="utf-8") as handle:
        for name in names:
            handle.write(name + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="通过上传接口把图片导入数据库")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--category", default="未分类")
    parser.add_argument("--batch-mb", type=int, default=20, help="单个请求最大体积（MB）")
    parser.add_argument("--batch-files", type=int, default=6, help="单个请求最多几张图")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_dir():
        print(f"[x] 图片目录不存在：{source}")
        return 1

    all_files = sorted(p for p in source.iterdir() if p.is_file())
    done = load_done()
    pending = [p for p in all_files if p.name not in done]

    print(f"目录：{source}")
    print(f"图片总数：{len(all_files)}，已上传：{len(done)}，待上传：{len(pending)}")
    if args.dry_run or not pending:
        return 0

    batches = make_batches(pending, args.batch_mb * 1024 * 1024, args.batch_files)
    print(f"分批：{len(batches)} 批（每批 <= {args.batch_mb}MB / {args.batch_files} 张）")

    credentials = (args.username, args.password)
    token = login(args.base_url, *credentials)
    start = time.time()
    uploaded = 0

    for index, batch in enumerate(batches, 1):
        result = upload_batch(
            args.base_url,
            batch,
            {"category": args.category},
            token,
            credentials,
        )
        count = result.get("count", len(batch))
        uploaded += count
        mark_done([p.name for p in batch])
        elapsed = time.time() - start
        speed = uploaded / elapsed if elapsed else 0
        print(
            f"[{index}/{len(batches)}] +{count} 张，累计 {uploaded}/{len(pending)}，"
            f"用时 {elapsed:.1f}s，{speed:.1f} 张/s",
            flush=True,
        )

    total = get_json(f"{args.base_url}/wallpapers/wallpapers/page/?page=1&pageSize=1").get("count")
    print(f"完成：本次上传 {uploaded} 张，数据库现有壁纸 {total} 条。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
