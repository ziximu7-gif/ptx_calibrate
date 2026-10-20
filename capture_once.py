from datetime import datetime
from pathlib import Path
import numpy as np
from scope_controller import TektronixScope
from phase_analysis import analyze_two_channels

from config import RF_FREQUENCY_HZ
rf_frequency = RF_FREQUENCY_HZ
MAX_POINTS = 10000

def main():
    scope = TektronixScope()

    try:
        # 1. 连接示波器
        print("正在连接示波器...")
        idn = scope.connect()
        print(f"设备：{idn}")

        # 2. 自动配置示波器
        print("正在配置采集参数...")
        scope.configure_acquisition(trigger_level=0.0)

        # 3. 等待用户确认
        input("\n确认信号稳定后，按 Enter 开始采集...")

        # 4. 开始单次采集，并等待完成
        print("正在采集...")
        scope.acquire_single(timeout_s=15)

        # 5. 读取两路波形
        print("正在读取 CH1...")
        t1, v1 = scope.read_waveform(
            1, max_points=MAX_POINTS
        )

        print("正在读取 CH2...")
        t2, v2 = scope.read_waveform(
            2, max_points=MAX_POINTS
        )
        if len(t1) != len(t2):
            raise ValueError("CH1、CH2 波形长度不一致")

        dt = float(np.median(np.diff(t1)))
        tolerance = max(abs(dt) * 1e-6, 1e-15)

        if not np.allclose(
            t1, t2, rtol=0, atol=tolerance
        ):
            raise ValueError(
                "CH1、CH2 时间轴不一致，需要检查采集设置"
            )

        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)

        filename = (
            datetime.now().strftime("%Y%m%d_%H%M%S")
            + "_capture.npz"
        )
        output_path = output_dir / filename

        np.savez_compressed(
            output_path,
            time=t1,
            reference_voltage=v1,
            rf_voltage=v2,
            frequency_hz=FREQUENCY_HZ,
            instrument_id=idn,
        )

        print(f"\n原始数据已保存：{output_path}")
        print(f"采样点数：{len(t1)}")
        print(f"采样率：{1 / dt / 1e6:.2f} MSa/s")
        print(f"记录时长：{(t1[-1] - t1[0]) * 1e6:.3f} us")

        # 检查采样率，避免明显欠采样
        if 1 / dt <= 2 * FREQUENCY_HZ:
            raise ValueError(
                "采样率不足以直接分析该 RF 载波"
            )

        if 1 / dt < 10 * FREQUENCY_HZ:
            print("警告：采样率低于载波频率的 10 倍。")

        print("\n正在拟合相位...")

        result = analyze_two_channels(
            t1, v1, v2, FREQUENCY_HZ
        )

        ref = result["reference"]
        rf = result["rf"]

        print("\n========== 测量结果 ==========")
        print(f"参考信号相位：{ref.phase_deg:+.3f}°")
        print(f"RF 信号相位：{rf.phase_deg:+.3f}°")
        print(
            "相位差："
            f"{result['phase_difference_deg']:+.3f}°"
        )
        print(f"参考信号拟合 R²：{ref.r_squared:.6f}")
        print(f"RF 信号拟合 R²：{rf.r_squared:.6f}")

        if (
            ref.r_squared < 0.98
            or rf.r_squared < 0.98
        ):
            print(
                "\n拟合质量较低，"
                "本次相位差不宜直接用于补偿。"
            )

    except Exception as exc:
        print(f"\n出错：{type(exc).__name__}: {exc}")

    finally:
        scope.close()
        print("\n示波器连接已关闭。")


if __name__ == "__main__":
    main()
