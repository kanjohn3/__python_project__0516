import streamlit as st
import matplotlib.pyplot as plt

# 頁面標題
st.title("手機品牌市占率圓餅圖")

# 中文字型設定
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

# 資料
labels = ['Nokia', 'Samsung', 'Apple', 'Lumia']
sizes = [20, 30, 45, 10]
colors = ['yellow', 'green', 'red', 'blue']
explode = [0.3, 0, 0, 0]

# 建立圖表
fig, ax = plt.subplots(figsize=(8, 8))

ax.pie(
    sizes,
    labels=labels,
    colors=colors,
    explode=explode,
    shadow=True,
    autopct='%1.1f%%',
    startangle=180
)

ax.axis('equal')

# 顯示在 Streamlit 網頁上
st.pyplot(fig)
