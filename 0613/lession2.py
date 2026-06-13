import requests
from requests import Response
import pandas as pd
from pandas import DataFrame
from pathlib import Path
import report
import tkinter as tk
from tkinter import messagebox
import threading

class YouBikeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouBike 2.0 資料下載工具")
        self.root.geometry("500x300")
        
        # 標題
        title_label = tk.Label(root, text="YouBike 2.0 資料下載與報表生成", font=("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        # 說明文本
        desc_label = tk.Label(root, text="點擊下方按鈕下載台北市 YouBike 2.0 資料\n並生成 PDF 報表", font=("Arial", 10))
        desc_label.pack(pady=10)
        
        # 下載按鈕
        self.download_btn = tk.Button(root, text="下載資料並生成報表", command=self.on_download, 
                                       font=("Arial", 11), bg="green", fg="white", padx=20, pady=10)
        self.download_btn.pack(pady=20)
        
        # 狀態標籤
        self.status_label = tk.Label(root, text="準備就緒", font=("Arial", 10), fg="blue")
        self.status_label.pack(pady=10)
        
        # 結果文本框
        self.result_text = tk.Text(root, height=8, width=60, font=("Courier", 9))
        self.result_text.pack(pady=10, padx=10)
        
    def on_download(self):
        """點擊下載按鈕時的事件"""
        # 禁用按鈕，防止重複點擊
        self.download_btn.config(state=tk.DISABLED)
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="正在下載...", fg="orange")
        
        # 在新執行緒中執行下載，避免 GUI 凍結
        thread = threading.Thread(target=self.download_data)
        thread.start()
    
    def download_data(self):
        """下載資料並生成報表（在背景執行緒中執行）"""
        try:
            # 台北市 YouBike 2.0 的 Web API 網址
            url: str = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"
            
            self.update_result("連線中...")
            
            # 使用 requests 套件裡面的 get 函式，執行後會傳出 Response 的實體
            response: Response = requests.get(url)
            
            if response.status_code == 200:  # 下載成功
                data: list[dict] = response.json()  # 使用 Response 實體的 json() 方法
                
                # list[dict] -> DataFrame
                df: DataFrame = pd.DataFrame(data=data)
                
                self.update_result(f"✓ 成功下載 {len(df)} 筆資料\n")
                self.update_result(f"資料欄位：\n{', '.join(df.columns.tolist())}\n\n")
                self.update_result(f"前 5 筆資料：\n{df.head().to_string()}\n\n")
                
                # Output path 是我們輸出的檔案的絕對路徑
                output_file = Path(__file__).with_name("youbike_report.pdf")
                
                self.update_result("正在生成 PDF 報表...")
                report.export_to_pdf(df, output_file)  # 呼叫自訂的 export_to_pdf function
                
                self.update_result(f"✓ 成功生成報表！\n檔案位置：{output_file}")
                self.root.after(0, lambda: messagebox.showinfo("成功", f"報表已生成！\n{output_file}"))
                self.status_label.config(text="下載完成", fg="green")
            else:
                self.update_result(f"✗ 下載失敗\n狀態碼：{response.status_code}")
                self.root.after(0, lambda: messagebox.showerror("失敗", f"下載失敗，狀態碼：{response.status_code}"))
                self.status_label.config(text="下載失敗", fg="red")
        
        except Exception as e:
            error_msg = f"✗ 發生錯誤：{str(e)}"
            self.update_result(error_msg)
            self.root.after(0, lambda: messagebox.showerror("錯誤", error_msg))
            self.status_label.config(text="發生錯誤", fg="red")
        
        finally:
            # 重新啟用按鈕
            self.download_btn.config(state=tk.NORMAL)
    
    def update_result(self, text: str):
        """更新結果文本框（安全地從背景執行緒更新）"""
        self.root.after(0, lambda: self._append_text(text))
    
    def _append_text(self, text: str):
        """在文本框最後追加文字"""
        self.result_text.insert(tk.END, text)
        self.result_text.see(tk.END)  # 自動捲到最後

def main():
    root = tk.Tk()
    app = YouBikeGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()