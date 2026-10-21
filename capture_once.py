from datetime import datetime
from pathlib import Path
import numpy as np
from scope_controller import TektronixScope
from phase_analysis import analyze_two_channels
import config as cfg

def main():
    scope = TektronixScope()
    try:
        # 1. 连接示波器
        print("正在连接示波器...")
        idn = scope.connect()
        print(f"设备：{idn}")
        # 2. 自动配置示波器
        print("正在配置采集参数...")
        scope.configure_acquisition()
        # 3. 开始采集
        input("\n确认信号稳定后，按 Enter 开始采集...")
        # 4. 开始单次采集，并等待完成
        print("正在采集...")
        scope.acquire_single()
        # 5. 读取两路波形
        print("正在读取参考信号...")
        t1, v1 = scope.read_waveform(cfg.REFERENCE_CHANNEL)
        print("正在读取 RF 信号...")
        t2, v2 = scope.read_waveform(cfg.RF_CHANNEL)
        if len(t1) != len(t2):
            raise ValueError("CH1、CH2 波形长度不一致")
        dt = float(np.median(np.diff(t1)))
        tolerance = max(abs(dt) * 1e-6, 1e-15)
        if not np.allclose(t1, t2, rtol=0, atol=tolerance):
            raise ValueError("CH1、CH2 时间轴不一致，需要检查采集设置")
        output_dir = Path(cfg.RESULTS_DIR)
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
            frequency_hz=cfg.RF_FREQUENCY_HZ,
            sample_rate_hz=1.0 / dt,
            reference_channel=cfg.REFERENCE_CHANNEL,
            rf_channel=cfg.RF_CHANNEL,
            instrument_id=idn,
        )
        print(f"\n原始数据已保存：{output_path}")
        print(f"采样点数：{len(t1)}")
        print(f"采样率：{1 / dt / 1e6:.2f} MSa/s")
        print(f"记录时长：{(t1[-1] - t1[0]) * 1e6:.3f} us")
        # 检查采样率，避免明显欠采样
        sample_rate = 1.0 / dt
        samples_per_cycle = (
            sample_rate / cfg.RF_FREQUENCY_HZ
        )
        print(
            f"每个 RF 周期采样点数: "
            f"{samples_per_cycle:.2f}"
        )
        if sample_rate <= 2 * cfg.RF_FREQUENCY_HZ:
            raise ValueError(
                "采样率不满足奈奎斯特条件，"
                "不执行相位拟合"
            )
        if samples_per_cycle < cfg.MIN_SAMPLES_PER_CYCLE:
            raise ValueError(
                f"每周期仅有 {samples_per_cycle:.2f} 个点，"
                f"低于配置要求 "
                f"{cfg.MIN_SAMPLES_PER_CYCLE} 个点"
            )
        if sample_rate < cfg.TARGET_SAMPLE_RATE_HZ:
            print(
                "提醒：实际采样率低于目标采样率，"
                "但已通过最低采样点数检查。"
            )
        print("\n正在拟合相位...")
        result = analyze_two_channels(t1,v1,v2,cfg.RF_FREQUENCY_HZ,)
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
            not np.isfinite(ref.r_squared)
            or not np.isfinite(rf.r_squared)
            or ref.r_squared < cfg.MIN_FIT_R_SQUARED
            or rf.r_squared < cfg.MIN_FIT_R_SQUARED
        ):
            print("拟合质量不足，本次结果无效")
            return
    except Exception as exc:
        print(f"\n出错：{type(exc).__name__}: {exc}")
    finally:
        scope.close()
if __name__ == "__main__":
    main()
