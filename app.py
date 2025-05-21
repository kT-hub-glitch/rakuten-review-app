# app.py ―― 楽天レビュー Scraper（商品番号入力版・全ページ取得）
# ------------------------------------------------------------------
import streamlit as st
import requests, re, io
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from bs4 import BeautifulSoup
import pandas as pd

st.title("楽天レビュー Scraper（商品番号だけで OK）")

item_code = st.text_input("商品番号を入力してください 例）374439_10002137")
go        = st.button("レビュー取得")

# ------------------------------------------------------------------
if go and item_code.strip():
    # ① 商品番号から 1 ページ目 URL を作成
    first_page_url = f"https://review.rakuten.co.jp/item/1/{item_code}"

    @st.cache_data(show_spinner=True)
    def scrape(start_url: str):
        ua = {"User-Agent": "Mozilla/5.0"}
        reviews = []

        # ② URL を分解 → 基本 URL とパラメータ名を決定
        u = urlsplit(start_url)
        q = parse_qs(u.query)
        param = "page" if "page" in q else ("p" if "p" in q else "p")

        # p/page を除いたベース URL（? が無ければクエリ部は空文字）
        q.pop("p", None); q.pop("page", None)
        base_url = urlunsplit((u.scheme, u.netloc, u.path, urlencode(q, doseq=True), ""))

        # ③ ページ番号を 1,2,3… と増やして取得
        page_num = 1
        while True:
            sep = "&" if "?" in base_url else "?"
            page_url = f"{base_url}{sep}{param}={page_num}"

            res = requests.get(page_url, headers=ua, timeout=15)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "lxml")
            body_list = soup.select(".review-body--3myhE")
            if not body_list:
                break   # レビューが無くなったら終了

            for body_div in body_list:
                tx = lambda d: d.get_text(strip=True) if d else ""
                title = tx(body_div.find_previous("div", class_="text-display--2xC98"))
                body  = tx(body_div)
                star  = tx(body_div.find_previous("div", class_="text-container--2tSUW"))
                date  = tx(body_div.find_previous(
                            "div", class_="text-display--2xC98",
                            string=lambda s: s and "注文日" in s)
                         ).replace("注文日：", "")
                color = tx(body_div.find_next(
                            "div", class_="text-display--2xC98",
                            string=lambda s: s and "カラー:" in s)
                         ).replace("タイプ:", "").replace("カラー:", "")
                age   = tx(body_div.find_next(
                            "div", class_="text-display--2xC98",
                            string=lambda s: s and re.match(r"\d+代", s)))

                reviews.append({
                    "ページ": page_num, "タイトル": title, "本文": body,
                    "星": star, "日付": date, "カラー": color, "年代": age
                })

            page_num += 1   # 次ページへ

        # ④ DataFrame 化 & 重複除去
        df = (pd.DataFrame(reviews)
                .drop_duplicates(subset=["タイトル", "本文", "星", "日付", "カラー", "年代"]))

        # ⑤ Excel 出力
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="reviews")
        bio.seek(0)
        return df, bio

    # -------------------- 実 行 --------------------
    try:
        df, excel_bytes = scrape(first_page_url)
        st.success(f"{len(df)} 件のレビューを取得しました")
        st.dataframe(df.head())

        st.download_button("=ﾘ袰  Excel ダウンロード",
                           data=excel_bytes,
                           file_name=f"rakuten_reviews_{item_code}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"エラー: {e}")

elif go:
    st.warning("商品番号を入力してください")
