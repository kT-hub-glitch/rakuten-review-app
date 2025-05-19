# app.py —— 楽天レビュー＋色＋年代 → Excel
# -----------------------------------------------
import streamlit as st
import requests, re, math, io
from bs4 import BeautifulSoup
import pandas as pd

st.title("楽天レビュー Scraper（色・年代対応）")

url = st.text_input("レビュー1ページ目の URL を入力してください")

if st.button("レビュー取得"):
    if not url.strip():
        st.warning("URL を入力してください")
        st.stop()

    @st.cache_data(show_spinner=True)
    def scrape(first_url: str):
        ua = {"User-Agent": "Mozilla/5.0"}
        reviews = []

        # ページ1
        res = requests.get(first_url, headers=ua, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")

        # 本文div が 1レビュー=1件
        box_list = soup.select(".review-body--3myhE")
        per_page = len(box_list) or 20  # 念のため

        # ページ送りの最後の数字
        nums = [
            int(b.get_text()) for b in
            soup.select(".container--21I6f .page-button--152RB")
            if b.get_text().isdigit()
        ]
        pages = max(nums) if nums else 1

        def make_url(n: int):
            if "p=" in first_url:
                return re.sub(r"p=\d+", f"p={n}", first_url)
            if "page=" in first_url:
                return re.sub(r"page=\d+", f"page={n}", first_url)
            sep = "&" if "?" in first_url else "?"
            return f"{first_url}{sep}p={n}"

        for p in range(1, pages + 1):
            html = requests.get(make_url(p), headers=ua, timeout=15).text
            sp = BeautifulSoup(html, "lxml")

            for body_div in sp.select(".review-body--3myhE"):
                # タイトル
                title_div = body_div.find_previous("div", class_="text-display--2xC98")
                title = title_div.get_text(strip=True) if title_div else ""
                # 本文
                body = body_div.get_text(strip=True)
                # 星
                rating_div = body_div.find_previous("div", class_="rating-container--1utdQ")
                star = rating_div.select_one(".text-container--2tSUW").get_text(strip=True) if rating_div else ""
                # 日付
                date_div = body_div.find_previous("div", class_="text-display--2xC98",
                                                  string=lambda s: s and "注文日" in s)
                date = date_div.get_text(strip=True).replace("注文日：", "") if date_div else ""

                # ★★★ 追 加 要 素 ★★★
                # 色 (タイプ / カラー)
                color_div = body_div.find_next("div", class_="text-display--2xC98",
                                               string=lambda s: s and "カラー:" in s)
                color = color_div.get_text(strip=True).replace("タイプ:", "").replace("カラー:", "") if color_div else ""

                # 年代（10代〜80代の数字＋代が入っているかで判断）
                age_div = body_div.find_next("div", class_="text-display--2xC98",
                                             string=lambda s: s and re.match(r"\d+代", s))
                age = age_div.get_text(strip=True) if age_div else ""

                reviews.append({
                    "ページ": p,
                    "タイトル": title,
                    "本文": body,
                    "星": star,
                    "日付": date,
                    "カラー": color,
                    "年代": age
                })

        df = pd.DataFrame(reviews)
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="reviews")
        bio.seek(0)
        return df, bio

    try:
        df, excel_bytes = scrape(url)
        st.success(f"{len(df)} 件を取得しました")
        st.dataframe(df.head())

        st.download_button("📥 Excel ダウンロード",
                           data=excel_bytes,
                           file_name="rakuten_reviews.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"エラー: {e}")
