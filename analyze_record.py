
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from phase_analysis import analyze_two_channels



def load_waveform(filename):
    """读取 MDO4104-6 保存的两路波形。"""

    with np.load(filename, allow_pickle=False) as data:

        t = np.asarray(
            data["time"], dtype=float
        )

        ch1 = np.asarray(
            data["reference_voltage"], dtype=float
        )

        ch2 = np.asarray(
            data["rf_voltage"], dtype=float
        )

        frequency = float(data["frequency_hz"])
        instrument_id = str(data["instrument_id"])

    print(f"示波器: {instrument_id}")
    print(f"配置频率: {frequency / 1e6:.3f} MHz")
    print(f"采样点数: {len(t)}")

    if not (len(t) == len(ch1) == len(ch2)):
        raise ValueError("两路波形与时间轴长度不一致")

    if len(t) < 10:
        raise ValueError("采样点不足")

    if np.any(np.diff(t) <= 0):
        raise ValueError("时间轴不是严格递增的")

    if not all(
        np.all(np.isfinite(x))
        for x in (t, ch1, ch2)
    ):
        raise ValueError("波形中存在非有限数值")

    return t, ch1, ch2


def plot_waveform(t, ch1, ch2, filename, frequency_hz=None):
    """绘制两路波形，保存 PNG。"""

    # 有频率参数时，优先查看前 20 个周期
    if frequency_hz is not None:
        end_time = t[0] + 20 / frequency_hz
        mask = t <= end_time

        if np.count_nonzero(mask) >= 10:
            t = t[mask]
            ch1 = ch1[mask]
            ch2 = ch2[mask]

    # 避免绘图点数过多
    step = max(1, len(t) // 5000)

    plt.figure(figsize=(11, 5))

    plt.plot(
        t[::step] * 1e6,
        ch1[::step],
        label="CH1 Reference",
    )

    plt.plot(
        t[::step] * 1e6,
        ch2[::step],
        label="CH2 RF",
        alpha=0.75,
    )

    plt.xlabel("Time (us)")
    plt.ylabel("Voltage (V)")
    plt.title("Oscilloscope Waveforms")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

    print(f"波形图已保存：{filename}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "file",
        help="NPZ 波形文件路径",
    )

    parser.add_argument(
        "--freq-mhz",
        type=float,
        default=None,
        help="拟合频率，单位 MHz",
    )

    args = parser.parse_args()
    filename = Path(args.file)

    t, ch1, ch2 = load_waveform(filename)

    dt = float(np.median(np.diff(t)))
    sample_rate = 1.0 / dt

    print(f"采样点数：{len(t)}")
    print(f"采样率：{sample_rate / 1e6:.3f} MSa/s")
    print(f"记录长度：{(t[-1] - t[0]) * 1e6:.3f} us")

    frequency_hz = None

    if args.freq_mhz is not None:
        frequency_hz = args.freq_mhz * 1e6

    plot_path = filename.with_name(
        filename.stem + "_waveform.png"
    )

    plot_waveform(
        t, ch1, ch2, plot_path, frequency_hz
    )

    if frequency_hz is None:
        print("未提供频率，仅完成波形检查。")
        return

    if frequency_hz <= 0 or frequency_hz >= sample_rate / 2:
        raise ValueError("拟合频率无效或超过采样奈奎斯特频率")

    result = analyze_two_channels(
        t,
        ch1,
        ch2,
        frequency_hz,
    )

    reference = result["reference"]
    rf = result["rf"]

    print("\n========== 拟合结果 ==========")
    print(f"CH1 振幅：{reference.amplitude:.6g} V")
    print(f"CH2 振幅：{rf.amplitude:.6g} V")
    print(f"CH1 R²：{reference.r_squared:.6f}")
    print(f"CH2 R²：{rf.r_squared:.6f}")

    # 第一版采用临时拟合质量门槛
    if (
        not np.isfinite(reference.r_squared)
        or not np.isfinite(rf.r_squared)
        or reference.r_squared < 0.95
        or rf.r_squared < 0.95
    ):
        print("\n波形不满足当前拟合质量要求。")
        print("不输出有效 RF 相位差。")
        return

    print(f"\n参考相位：{reference.phase_deg:.3f}°")
    print(f"RF 相位：{rf.phase_deg:.3f}°")
    print(
        f"相位差："
        f"{result['phase_difference_deg']:+.3f}°"
    )


if __name__ == "__main__":
    main()
