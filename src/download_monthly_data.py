"""
下載交通部觀光署 2023 年起、目前已發布的逐月觀光旅館營運月報。

官方月報部分為「年初至當月累計」資料；本程式只下載原始檔，
不覆蓋既有年度檔案，檔案存放於 data/raw/monthly/YYYYMM.xlsx。
"""

from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import re
import zipfile

import requests


ROOT = Path(__file__).resolve().parent.parent
RAW_MONTHLY_DIR = ROOT / "data" / "raw" / "monthly"
INDEX_URL = "https://admin.taiwan.net.tw/businessinfo/FilePage?a=10425"
BASE_URL = "https://admin.taiwan.net.tw"
HEADERS = {"User-Agent": "Mozilla/5.0"}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": [], "hrefs": [], "links": []}
            self.row.append(self.cell)
        elif tag == "a" and self.cell is not None:
            self.anchor = {"href": attrs.get("href"), "text": []}

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor["text"].append(data)
        elif self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a":
            if self.cell is not None and self.anchor and self.anchor["href"]:
                self.cell["links"].append(self.anchor)
                self.cell["hrefs"].append(self.anchor["href"])
            self.anchor = None
        elif tag in {"td", "th"}:
            self.anchor = None
            self.cell = None
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = None


def clean_text(parts):
    return " ".join(unescape("".join(parts)).split())


def find_monthly_files():
    found = {}
    for page in range(1, 16):
        url = INDEX_URL if page == 1 else f"{INDEX_URL}&P={page}"
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        parser = TableParser()
        parser.feed(response.text)

        for row in parser.rows:
            texts = [clean_text(cell["text"]) for cell in row]
            title = next((t for t in texts if "觀光旅館營運月報" in t), "")
            # 只取 YYYYMM 單月檔；排除 YYYY01-12、YYYY01-03 等區間檔。
            # 年份不寫死，讓官方新增月份後可直接更新。
            match = re.match(r"^((?:20)\d{2}(?:0[1-9]|1[0-2]))(?![-\d])", title.strip())
            if not match:
                continue
            yyyymm = match.group(1)
            if int(yyyymm[:4]) < 2023:
                continue
            xlsx = None
            for cell in row:
                for link in cell["links"]:
                    link_text = clean_text(link["text"]).upper()
                    if "XLSX" in link_text and "ATTFILE" in unescape(link["href"]).upper():
                        xlsx = link["href"]
                        break
                if xlsx:
                    break
            if xlsx:
                found[yyyymm] = urljoin(BASE_URL, unescape(xlsx))

    if not found:
        raise RuntimeError("官方頁面找不到 2023 年起的單月 XLSX 檔案")

    latest = max(found)
    latest_year, latest_month = int(latest[:4]), int(latest[4:])
    missing = [
        f"{year}{month:02d}"
        for year in range(2023, latest_year + 1)
        for month in range(1, 13)
        if (year < latest_year or month <= latest_month)
        and f"{year}{month:02d}" not in found
    ]
    if missing:
        raise RuntimeError(f"官方頁面找不到月份檔案：{', '.join(missing)}")
    return dict(sorted(found.items()))


def download_all():
    RAW_MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    files = find_monthly_files()
    downloaded = 0
    skipped = 0
    for yyyymm, url in files.items():
        path = RAW_MONTHLY_DIR / f"{yyyymm}.xlsx"
        if path.exists():
            is_xlsx = False
            try:
                with zipfile.ZipFile(path) as archive:
                    is_xlsx = "[Content_Types].xml" in archive.namelist()
            except zipfile.BadZipFile:
                is_xlsx = False
            if is_xlsx:
                print(f"[{yyyymm}] 已存在，略過：{path.name}")
                skipped += 1
                continue
            print(f"[{yyyymm}] 發現非 XLSX 檔，重新下載：{path.name}")
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
        print(f"[{yyyymm}] 完成：{path.name} ({path.stat().st_size / 1024:.1f} KB)")
        downloaded += 1
    print(f"\n完成：下載 {downloaded} 份，略過既有檔案 {skipped} 份")
    print(f"資料位置：{RAW_MONTHLY_DIR}")


if __name__ == "__main__":
    download_all()
