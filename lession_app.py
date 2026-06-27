import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# =========================
# 中文字型設定
# =========================
plt.rcParams['font.sans-serif'] = [
    'Microsoft JhengHei',  # Windows 常見
    'Arial Unicode MS',    # macOS 常見
    'Heiti TC',            # macOS 常見
    'DejaVu Sans'          # 備援
]
plt.rcParams['axes.unicode_minus'] = False

# =========================
# 建立資料
# =========================
x = np.linspace(0, 4 * np.pi, 1000)

# 初始參數
A0 = 1.0
w0 = 1.0
phi0 = 0.0

# =========================
# 建立圖表與主繪圖區
# =========================
fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.28)

# 初始波形
y_sin = A0 * np.sin(w0 * x + phi0)
y_cos = A0 * np.cos(w0 * x + phi0)

sin_line, = ax.plot(x, y_sin, color='red', linestyle='-', label='正弦波 sin')
cos_line, = ax.plot(x, y_cos, color='blue', linestyle='--', label='餘弦波 cos')

ax.set_title('正弦與餘弦波形互動式繪圖')
ax.set_xlabel('x 軸')
ax.set_ylabel('y 軸')
ax.set_xlim(0, 4 * np.pi)
ax.grid(True)
ax.legend(loc='upper right')

# =========================
# 建立滑桿區域
# =========================
ax_amp = fig.add_axes([0.15, 0.18, 0.7, 0.03])
ax_freq = fig.add_axes([0.15, 0.12, 0.7, 0.03])
ax_phase = fig.add_axes([0.15, 0.06, 0.7, 0.03])

amp_slider = Slider(ax_amp, '振幅 A', 0.1, 5.0, valinit=A0)
freq_slider = Slider(ax_freq, '頻率 ω', 0.1, 10.0, valinit=w0)
phase_slider = Slider(ax_phase, '相位 φ', 0.0, 2 * np.pi, valinit=phi0)

# =========================
# 更新函式
# =========================
def update(val):
    A = amp_slider.val
    w = freq_slider.val
    phi = phase_slider.val

    sin_line.set_ydata(A * np.sin(w * x + phi))
    cos_line.set_ydata(A * np.cos(w * x + phi))
    fig.canvas.draw_idle()

amp_slider.on_changed(update)
freq_slider.on_changed(update)
phase_slider.on_changed(update)

# =========================
# 顯示視窗
# =========================
plt.show()