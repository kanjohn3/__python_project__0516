import pandas as pd
import tkinter as tk
from tkinter import ttk

# ───────────────────────── 資料處理 ─────────────────────────

# 讀取 CSV 檔案，第一列作為欄位名稱
df = pd.read_csv('各鄉鎮市區人口密度.csv', header=0)

# 移除最後 5 筆非資料內容（尾部說明資訊）
df = df.iloc[:-5]

# 僅保留 'site_id'（區域別）、'people_total'（年底人口數）、'area'（土地面積）三個欄位
df = df[['site_id', 'people_total', 'area']].copy()

# 重新命名欄位
df.rename(columns={
    'site_id': '區域別',
    'people_total': '人口數',
    'area': '土地面積'
}, inplace=True)

# 將 '人口數' 與 '土地面積' 轉換為數值型態，無法轉換者設為 NaN
df['人口數'] = pd.to_numeric(df['人口數'], errors='coerce')
df['土地面積'] = pd.to_numeric(df['土地面積'], errors='coerce')

# 移除含有空值（NaN）的列
df.dropna(subset=['人口數', '土地面積'], inplace=True)

# 新增 '人口密度' 欄位：人口數 / 土地面積
df['人口密度'] = df['人口數'] / df['土地面積']

# ───────────────────────── GUI 介面 ─────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        self.root.title('台灣鄉鎮市區人口密度查詢系統')
        self.root.geometry('900x600')

        # 儲存原始資料（DataFrame 副本，避免後續操作污染）
        self.data = df.copy()

        # ── 上方控制區 ──
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=10)

        ttk.Label(control_frame, text='選擇區域名稱：').pack(side=tk.LEFT)
        self.keyword_combo = ttk.Combobox(control_frame, width=27, state='normal')
        self.keyword_combo.pack(side=tk.LEFT, padx=5)
        self.keyword_combo.set('')
        ttk.Button(control_frame, text='查詢', command=self.query).pack(side=tk.LEFT)

        # ── 下方表格區 ──
        table_frame = ttk.Frame(root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 建立 Treeview 與滾動條
        columns = ('區域別', '人口數', '土地面積', '人口密度')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 設定各欄位標題、寬度與置中對齊
        col_center = tk.CENTER
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=180, anchor=col_center)

        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # 載入所有資料
        self.load_data(self.data)

        # 將所有區域別填入下拉式選單
        self.keyword_combo['values'] = sorted(self.data['區域別'].tolist())

    def load_data(self, data):
        """將給定的 DataFrame 資料載入 Treeview 表格"""
        # 清除現有資料
        for row in self.tree.get_children():
            self.tree.delete(row)

        # 逐筆插入資料
        for _, row in data.iterrows():
            self.tree.insert('', tk.END, values=(
                row['區域別'],
                int(row['人口數']),              # 人口數顯示為整數
                f"{row['土地面積']:.2f}",         # 保留小數點後兩位
                f"{row['人口密度']:.2f}"           # 人口密度四捨五入至小數點後兩位
            ))

    def query(self):
        """根據關鍵字篩選區域別，並更新表格"""
        keyword = self.keyword_combo.get().strip()
        if keyword == '':
            # 無關鍵字則顯示所有資料
            filtered = self.data
        else:
            # 篩選「區域別」包含關鍵字的列（不分大小寫）
            filtered = self.data[self.data['區域別'].str.contains(keyword, na=False)]
        self.load_data(filtered)


# ───────────────────────── 啟動應用程式 ─────────────────────────

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
