"""ui_theme.py — 放在 app 同一資料夾。只負責外觀，不動任何交易邏輯。
台股慣例：紅=漲/停利/壓力，綠=跌/停損/支撐。"""
import streamlit as st

UP, DOWN, ACCENT = "#F6465D", "#1FC98B", "#4C8DFF"

_CSS = f"""
<style>
:root {{
  --bg:#0B1018; --panel:#121A26; --panel2:#182233; --line:#243248;
  --text:#E6EBF3; --muted:#8A97AD; --up:{UP}; --down:{DOWN}; --accent:{ACCENT};
}}
/* 基底：只設一次文字色，不再用 !important 蓋掉所有 div/span */
.stApp {{ background:var(--bg); color:var(--text); }}
html, body, [class*="css"] {{ font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif; }}
h1 {{ font-size:1.6rem !important; font-weight:700 !important; letter-spacing:.3px; }}
h2, h3, h4 {{ font-weight:650 !important; }}
.block-container {{ padding-top:1.4rem; max-width:1200px; }}
#MainMenu, footer {{ visibility:hidden; }}

/* 側邊欄：選單像導覽列 */
[data-testid="stSidebar"] {{ background:var(--panel); border-right:1px solid var(--line); }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
  padding:9px 12px; border-radius:10px; margin-bottom:2px; width:100%;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background:var(--panel2); }}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background:rgba(76,141,255,.16); box-shadow:inset 3px 0 0 var(--accent);
}}

/* 分頁：膠囊式，觸控友善 */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{
  background:var(--panel); border:1px solid var(--line); border-radius:999px;
  padding:6px 16px; height:auto;
}}
.stTabs [aria-selected="true"] {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}

/* 按鈕：次要按鈕低調，主要按鈕醒目；最小高度方便手指點 */
.stButton>button {{
  min-height:42px; border-radius:10px; border:1px solid var(--line);
  background:var(--panel2); color:var(--text); font-weight:600;
}}
.stButton>button:hover {{ border-color:var(--accent); color:#fff; }}
.stButton>button[kind="primary"] {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.stButton>button:disabled {{ opacity:.45; }}

/* 輸入元件 */
input, [data-baseweb="select"] > div {{ background:var(--panel2) !important; border-radius:10px !important; }}

/* Streamlit 原生 metric / expander */
[data-testid="stMetric"] {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:10px 14px; }}
[data-testid="stMetricLabel"] {{ color:var(--muted); }}
.stExpander {{ background:var(--panel); border:1px solid var(--line) !important; border-radius:12px; }}

/* 台股色彩 */
.up {{ color:var(--up); }} .down {{ color:var(--down); }} .flat {{ color:var(--muted); }}
.muted {{ color:var(--muted); font-size:.85rem; }}

/* 個股列：左側色條表示漲跌，一眼分辨 */
.row {{
  display:flex; justify-content:space-between; align-items:center; gap:12px;
  background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--muted);
  border-radius:12px; padding:12px 16px; margin:8px 0 4px;
}}
.row.up-bar {{ border-left-color:var(--up); }} .row.down-bar {{ border-left-color:var(--down); }}
.row .name {{ font-size:1.05rem; font-weight:700; }}
.row .code {{ color:var(--muted); font-size:.85rem; margin-left:8px; }}
.row .px {{ font-size:1.25rem; font-weight:800; text-align:right; line-height:1.2; }}
.row .px small {{ display:block; font-size:.85rem; font-weight:600; }}
.tag {{ display:inline-block; margin-top:4px; padding:2px 10px; border-radius:999px;
        background:var(--panel2); color:var(--muted); font-size:.78rem; }}

/* 報價橫幅（盯盤頁最上方） */
.quote {{
  background:linear-gradient(135deg,#142033,#0F1826); border:1px solid var(--line);
  border-radius:16px; padding:18px 22px; margin:6px 0 14px;
}}
.quote .big {{ font-size:2.4rem; font-weight:800; line-height:1.1; }}
.quote .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:10px; margin-top:12px; }}
.quote .cell {{ background:rgba(255,255,255,.03); border-radius:10px; padding:8px 12px; }}
.quote .cell b {{ display:block; font-size:1.05rem; }}

/* 價位卡（停損/停利） */
.lv {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px 16px; height:100%; }}
.lv h5 {{ margin:0 0 8px; font-size:.95rem; }}
.lv .it {{ display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px dashed var(--line); }}
.lv .it:last-child {{ border-bottom:0; }}

/* 手機：縮小標題與間距，欄位自動堆疊 */
@media (max-width:640px) {{
  .block-container {{ padding:.8rem .6rem; }}
  h1 {{ font-size:1.25rem !important; }}
  .quote .big {{ font-size:1.9rem; }}
  .row {{ padding:10px 12px; }}
}}
</style>
"""


def inject_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def tone(pct) -> str:
    pct = float(pct)
    return "up" if pct > 0 else ("down" if pct < 0 else "flat")


def stock_row(idx, code, name, price, pct, tag="") -> str:
    t = tone(pct)
    bar = {"up": "up-bar", "down": "down-bar"}.get(t, "")
    tag_html = f'<span class="tag">{tag}</span>' if tag else ""
    return (
        f'<div class="row {bar}"><div>'
        f'<span class="name">{name}</span><span class="code">{code}</span><br>{tag_html}</div>'
        f'<div class="px {t}">{price}<small>{float(pct):+.2f}%</small></div></div>'
    )


def quote_banner(code, name, price, open_p, high, low, volume, bias, momentum, balance) -> str:
    pct = (price - open_p) / open_p * 100 if open_p else 0
    t = tone(pct)
    cells = [("開盤", f"{open_p:.2f}"), ("最高", f"{high:.2f}"), ("最低", f"{low:.2f}"),
             ("成交量(張)", f"{volume:,}"), ("成本乖離", f"{bias:+.2f}%"),
             ("動能係數", f"{momentum:.2f}"), ("多空平衡點", f"{balance:.2f}")]
    grid = "".join(f'<div class="cell"><span class="muted">{k}</span><b>{v}</b></div>' for k, v in cells)
    return (
        f'<div class="quote"><span class="muted">{code}</span> <b>{name}</b>'
        f'<div class="big {t}">{price:.2f} <span style="font-size:1.1rem">{pct:+.2f}%</span></div>'
        f'<div class="grid">{grid}</div></div>'
    )


def level_card(title, items, color_class) -> str:
    """items: [(label, price_float), ...]；color_class 傳 'down'(停損) 或 'up'(停利)"""
    rows = "".join(
        f'<div class="it"><span class="muted">{k}</span><b class="{color_class}">{v:.2f}</b></div>'
        for k, v in items
    )
    return f'<div class="lv"><h5 class="{color_class}">{title}</h5>{rows}</div>'
