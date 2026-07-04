# -*- coding: utf-8 -*-
"""
台灣股票四檔互動分析工具
========================

功能：
1. 使用 `twstock` 套件內建的全台股（上市 + 上櫃）代碼／名稱資料庫，
   提供可搜尋（輸入代碼或中文名稱皆可）的下拉選單，讓你任意挑選 4 檔股票。
2. 按下「下載並分析」後，透過 `yfinance` 即時下載這 4 檔股票的歷史股價，
   並自動判斷上市（.TW）／上櫃（.TWO）後綴。
3. 動態產生 4 種分析圖表（走勢比較、均線、報酬相關性、風險報酬），
   並提供「即時報價」面板（透過 twstock.realtime 每隔數秒刷新一次）。

安裝需求（終端機執行）：
    pip install twstock yfinance pandas numpy matplotlib

執行方式：
    python tw_stock_analyzer.py

注意事項：
- twstock 的即時報價是靠爬取公開資訊觀測站/證交所網頁，非官方 API，
  盤中才有資料、且偶爾會因對方網站調整而失敗，屬正常現象，程式已做例外處理。
- 本工具僅為資料呈現與學習用途，不構成任何投資建議。
"""

import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import twstock
import yfinance as yf

# ---------------------------------------------------------------------------
# 中文字型設定（依作業系統嘗試不同字型，避免圖表中文變成方框）
# ---------------------------------------------------------------------------
plt.rcParams["font.sans-serif"] = [
    "Microsoft JhengHei", "PingFang TC", "Heiti TC",
    "Noto Sans CJK TC", "SimHei", "Arial Unicode MS",
]
plt.rcParams["axes.unicode_minus"] = False

REFRESH_MS = 15000  # 即時報價刷新間隔（毫秒）


# ---------------------------------------------------------------------------
# 可搜尋下拉選單（輸入部分代碼或名稱即可篩選）
# ---------------------------------------------------------------------------
class SearchableCombobox(ttk.Combobox):
    def __init__(self, master, all_values, **kwargs):
        super().__init__(master, **kwargs)
        self._all_values = all_values
        self["values"] = self._all_values
        self.bind("<KeyRelease>", self._on_keyrelease)

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Tab"):
            return
        typed = self.get().strip().lower()
        if typed == "":
            self["values"] = self._all_values
        else:
            self["values"] = [v for v in self._all_values if typed in v.lower()]
        # 篩選後自動展開下拉清單，方便挑選
        try:
            self.event_generate("<Down>")
        except tk.TclError:
            pass


def build_stock_choice_list():
    """從 twstock.codes 建立 '代碼 名稱 (市場)' 的清單，做為下拉選單資料來源。"""
    choices = []
    for code, info in twstock.codes.items():
        if info.type != "股票":
            continue
        choices.append(f"{code} {info.name} ({info.market})")
    return sorted(choices)


def parse_choice(choice_str):
    """將 '2330 台積電 (上市)' 拆解成 (code, name, market)。"""
    code = choice_str.split(" ", 1)[0]
    rest = choice_str[len(code):].strip()
    name = rest.split(" (")[0]
    market = rest.split("(")[-1].rstrip(")")
    return code, name, market


def yf_ticker(code, market):
    suffix = ".TWO" if "櫃" in market else ".TW"
    return f"{code}{suffix}"


# ---------------------------------------------------------------------------
# 主應用程式
# ---------------------------------------------------------------------------
class StockAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("台股四檔互動分析工具")
        self.root.geometry("1180x760")

        self.stock_choices = build_stock_choice_list()
        self.selected_vars = []
        self.comboboxes = []
        self.selected_stocks = []  # [(code, name, market), ...]
        self.price_df = None       # 4 檔收盤價 DataFrame，欄位為股票名稱
        self.gui_queue = queue.Queue()
        self.realtime_job = None

        self._build_top_frame()
        self._build_status_bar()
        self._build_notebook()

        self.root.after(200, self._poll_queue)

    # ------------------------------------------------------------------
    # 介面建構
    # ------------------------------------------------------------------
    def _build_top_frame(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="請選擇 4 檔股票（可輸入代碼或名稱搜尋）：",
                  font=("Microsoft JhengHei", 11, "bold")).grid(
            row=0, column=0, columnspan=8, sticky="w", pady=(0, 6))

        for i in range(4):
            ttk.Label(top, text=f"股票 {i + 1}：").grid(row=1, column=i * 2, sticky="e", padx=(0, 4))
            cb = SearchableCombobox(top, self.stock_choices, width=22)
            cb.grid(row=1, column=i * 2 + 1, padx=(0, 12), pady=4)
            self.comboboxes.append(cb)

        # 預設帶入常見範例，方便第一次使用
        defaults = ["2330", "2317", "2454", "0050"]
        for cb, code in zip(self.comboboxes, defaults):
            match = next((c for c in self.stock_choices if c.startswith(code + " ")), None)
            if match:
                cb.set(match)

        ttk.Label(top, text="資料期間：").grid(row=2, column=0, sticky="e", pady=(8, 0))
        self.period_var = tk.StringVar(value="6mo")
        period_box = ttk.Combobox(top, textvariable=self.period_var, width=10, state="readonly",
                                   values=["1mo", "3mo", "6mo", "1y", "2y", "5y"])
        period_box.grid(row=2, column=1, sticky="w", pady=(8, 0))

        self.analyze_btn = ttk.Button(top, text="⬇ 下載並分析", command=self.on_analyze_click)
        self.analyze_btn.grid(row=2, column=2, columnspan=2, sticky="w", padx=(20, 0), pady=(8, 0))

        self.realtime_var = tk.BooleanVar(value=False)
        realtime_chk = ttk.Checkbutton(top, text="啟用即時報價（每 15 秒刷新，僅盤中有效）",
                                        variable=self.realtime_var, command=self.on_toggle_realtime)
        realtime_chk.grid(row=2, column=4, columnspan=4, sticky="w", padx=(20, 0), pady=(8, 0))

        # 即時報價面板
        rt_frame = ttk.LabelFrame(self.root, text="即時報價", padding=8)
        rt_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.realtime_labels = []
        for i in range(4):
            lbl = ttk.Label(rt_frame, text=f"股票 {i + 1}：尚未載入", font=("Consolas", 11))
            lbl.grid(row=0, column=i, padx=20, sticky="w")
            self.realtime_labels.append(lbl)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="請選擇 4 檔股票後按「下載並分析」。")
        bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w", padding=4)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.fig_trend = Figure(figsize=(10, 5.5), dpi=100)
        self.fig_ma = Figure(figsize=(10, 5.5), dpi=100)
        self.fig_corr = Figure(figsize=(10, 5.5), dpi=100)
        self.fig_risk = Figure(figsize=(10, 5.5), dpi=100)

        self.tab_trend = self._add_fig_tab("① 走勢比較（基期=100）", self.fig_trend)
        self.tab_ma = self._add_fig_tab("② 均線分析（MA5 / MA20）", self.fig_ma)
        self.tab_corr = self._add_fig_tab("③ 報酬率相關性", self.fig_corr)
        self.tab_risk = self._add_fig_tab("④ 風險報酬散佈", self.fig_risk)

    def _add_fig_tab(self, title, fig):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()
        return canvas

    # ------------------------------------------------------------------
    # 下載與分析（背景執行緒，避免介面凍結）
    # ------------------------------------------------------------------
    def on_analyze_click(self):
        choices = [cb.get().strip() for cb in self.comboboxes]
        if any(c == "" for c in choices):
            messagebox.showwarning("提醒", "請確認 4 個欄位都已選擇股票。")
            return
        if len(set(c.split(" ", 1)[0] for c in choices)) < 4:
            messagebox.showwarning("提醒", "請選擇 4 檔『不同』的股票。")
            return

        try:
            self.selected_stocks = [parse_choice(c) for c in choices]
        except Exception:
            messagebox.showerror("錯誤", "股票選擇格式有誤，請重新從下拉選單挑選。")
            return

        self.analyze_btn.config(state=tk.DISABLED)
        self.status_var.set("下載中，請稍候...")
        threading.Thread(target=self._download_and_analyze, daemon=True).start()

    def _download_and_analyze(self):
        try:
            tickers = [yf_ticker(code, market) for code, name, market in self.selected_stocks]
            names = [name for code, name, market in self.selected_stocks]
            period = self.period_var.get()

            data = yf.download(tickers, period=period, auto_adjust=True,
                                progress=False, group_by="ticker", threads=True)

            close_cols = {}
            for ticker, name in zip(tickers, names):
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        series = data[ticker]["Close"]
                    else:
                        series = data["Close"]
                    close_cols[name] = series
                except Exception:
                    close_cols[name] = pd.Series(dtype=float)

            df = pd.DataFrame(close_cols).dropna(how="all")
            if df.empty or df.shape[0] < 2:
                self.gui_queue.put(("error", "下載失敗或資料不足，請確認股票代碼或稍後再試。"))
                return

            self.price_df = df
            self.gui_queue.put(("analyzed", None))
        except Exception as exc:
            self.gui_queue.put(("error", f"下載發生錯誤：{exc}"))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.gui_queue.get_nowait()
                if kind == "analyzed":
                    self._render_all_charts()
                    self.status_var.set(
                        f"分析完成（資料區間：{self.price_df.index[0].date()} ~ {self.price_df.index[-1].date()}）")
                    self.analyze_btn.config(state=tk.NORMAL)
                elif kind == "error":
                    messagebox.showerror("錯誤", payload)
                    self.status_var.set("發生錯誤，請重新嘗試。")
                    self.analyze_btn.config(state=tk.NORMAL)
                elif kind == "realtime":
                    self._update_realtime_labels(payload)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    # ------------------------------------------------------------------
    # 圖表繪製
    # ------------------------------------------------------------------
    def _render_all_charts(self):
        self._plot_trend()
        self._plot_ma()
        self._plot_correlation()
        self._plot_risk_return()

    def _plot_trend(self):
        fig = self.fig_trend
        fig.clear()
        ax = fig.add_subplot(111)
        normalized = self.price_df / self.price_df.iloc[0] * 100
        for col in normalized.columns:
            ax.plot(normalized.index, normalized[col], label=col, linewidth=1.8)
        ax.set_title("股價走勢比較（起始日 = 100）")
        ax.set_xlabel("日期")
        ax.set_ylabel("指數化價格")
        ax.legend(loc="best")
        ax.grid(alpha=0.3)
        fig.autofmt_xdate()
        fig.tight_layout()
        self.tab_trend.draw()

    def _plot_ma(self):
        fig = self.fig_ma
        fig.clear()
        cols = list(self.price_df.columns)
        for i, col in enumerate(cols):
            ax = fig.add_subplot(2, 2, i + 1)
            series = self.price_df[col]
            ma5 = series.rolling(5).mean()
            ma20 = series.rolling(20).mean()
            ax.plot(series.index, series, label="收盤價", linewidth=1.2, color="black")
            ax.plot(ma5.index, ma5, label="MA5", linewidth=1.2)
            ax.plot(ma20.index, ma20, label="MA20", linewidth=1.2)
            ax.set_title(col, fontsize=10)
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            ax.tick_params(axis="x", labelrotation=30, labelsize=7)
        fig.tight_layout()
        self.tab_ma.draw()

    def _plot_correlation(self):
        fig = self.fig_corr
        fig.clear()
        returns = self.price_df.pct_change().dropna()
        corr = returns.corr()

        ax1 = fig.add_subplot(1, 2, 1)
        im = ax1.imshow(corr, vmin=-1, vmax=1, cmap="RdYlGn")
        ax1.set_xticks(range(len(corr.columns)))
        ax1.set_yticks(range(len(corr.columns)))
        ax1.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
        ax1.set_yticklabels(corr.columns, fontsize=8)
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                ax1.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
        ax1.set_title("日報酬率相關係數")
        fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)

        ax2 = fig.add_subplot(1, 2, 2)
        avg_ret = returns.mean() * 100
        bars = ax2.bar(avg_ret.index, avg_ret.values,
                        color=["#2ca02c" if v >= 0 else "#d62728" for v in avg_ret.values])
        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_title("平均日報酬率 (%)")
        ax2.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax2.grid(alpha=0.3, axis="y")
        for b in bars:
            h = b.get_height()
            ax2.annotate(f"{h:.3f}%", (b.get_x() + b.get_width() / 2, h),
                         ha="center", va="bottom" if h >= 0 else "top", fontsize=7)
        fig.tight_layout()
        self.tab_corr.draw()

    def _plot_risk_return(self):
        fig = self.fig_risk
        fig.clear()
        ax = fig.add_subplot(111)
        returns = self.price_df.pct_change().dropna()
        ann_return = returns.mean() * 252 * 100
        ann_vol = returns.std() * np.sqrt(252) * 100

        for name in self.price_df.columns:
            ax.scatter(ann_vol[name], ann_return[name], s=140)
            ax.annotate(name, (ann_vol[name], ann_return[name]),
                        textcoords="offset points", xytext=(8, 6), fontsize=9)

        ax.axhline(0, color="grey", linewidth=0.8)
        ax.set_xlabel("年化波動度 (%)")
        ax.set_ylabel("年化報酬率 (%)")
        ax.set_title("風險 vs 報酬（依所選期間估算）")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        self.tab_risk.draw()

    # ------------------------------------------------------------------
    # 即時報價
    # ------------------------------------------------------------------
    def on_toggle_realtime(self):
        if self.realtime_var.get():
            if not self.selected_stocks:
                messagebox.showinfo("提示", "請先按「下載並分析」選定股票，再啟用即時報價。")
                self.realtime_var.set(False)
                return
            self._schedule_realtime()
        else:
            if self.realtime_job:
                self.root.after_cancel(self.realtime_job)
                self.realtime_job = None

    def _schedule_realtime(self):
        threading.Thread(target=self._fetch_realtime, daemon=True).start()
        self.realtime_job = self.root.after(REFRESH_MS, self._schedule_realtime)

    def _fetch_realtime(self):
        codes = [s[0] for s in self.selected_stocks]
        try:
            result = twstock.realtime.get(codes)
        except Exception as exc:
            result = {"__error__": str(exc)}
        self.gui_queue.put(("realtime", result))

    def _update_realtime_labels(self, result):
        if "__error__" in result:
            for lbl in self.realtime_labels:
                lbl.config(text="即時報價暫時無法取得（盤後或來源異常）")
            return
        for i, (code, name, market) in enumerate(self.selected_stocks):
            info = result.get(code)
            if not info or not info.get("success"):
                self.realtime_labels[i].config(text=f"{code} {name}：無即時資料（可能未開盤）")
                continue
            rt = info["realtime"]
            try:
                price = float(rt["latest_trade_price"])
                open_p = float(rt["open"])
                change = price - open_p
                pct = (change / open_p * 100) if open_p else 0
                arrow = "▲" if change > 0 else ("▼" if change < 0 else "－")
                self.realtime_labels[i].config(
                    text=f"{code} {name}：{price:.2f} {arrow}{abs(change):.2f} ({pct:+.2f}%)")
            except (KeyError, ValueError, TypeError):
                self.realtime_labels[i].config(text=f"{code} {name}：資料格式異常")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        style.theme_use("clam")
    except tk.TclError:
        pass
    app = StockAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
