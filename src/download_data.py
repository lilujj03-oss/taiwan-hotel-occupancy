"""
download_data.py
下載交通部觀光署 2023–2025 年觀光旅館營運統計 XLSX 資料
執行方式：python src/download_data.py
"""

import os
import requests
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 觀光署官方檔案連結（依實際年份更新）
FILES = {
    "2023": "https://admin.taiwan.net.tw/fapi/AttFile?id=31761&type=AttFile",
    "2024": "https://admin.taiwan.net.tw/fapi/AttFile?id=36837&type=AttFile",
    "2025": "https://admin.taiwan.net.tw/fapi/AttFile?id=40320&type=AttFile",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def download_file(year: str, url: str) -> Path:
    save_path = RAW_DIR / f"hotel_{year}.xlsx"
    if save_path.exists():
        print(f"[{year}] 已存在，略過下載：{save_path.name}")
        return save_path

    print(f"[{year}] 下載中...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
        size_kb = save_path.stat().st_size / 1024
        print(f"[{year}] 完成 → {save_path.name} ({size_kb:.1f} KB)")
    except requests.RequestException as e:
        print(f"[{year}] 下載失敗：{e}")
        print(f"  請手動下載 {url}")
        print(f"  並儲存為 {save_path}")
        return None
    return save_path


def main():
    print("=" * 50)
    print("觀光旅館營運統計資料下載")
    print("=" * 50)
    for year, url in FILES.items():
        download_file(year, url)
    print("\n下載完成，檔案位置：", RAW_DIR)


if __name__ == "__main__":
    main()
