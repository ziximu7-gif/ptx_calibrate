import csv
from datetime import datetime
from pathlib import Path
import numpy as np
import config as cfg
from scope_controller import TektronixScope
from phase_analysis import analyze_two_channels, wrap_degrees
def main():
    scope = TektronixScope()
    output_dir = (
        Path(cfg.RESULTS_DIR)
        / datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    phase_differences = []
    fit_qualities = []
    try:
        print("MRI 8-Channel RF Phase Calibration")
        print(f"RF Frequency: {cfg.RF_FREQUENCY_HZ / 1e6} MHz")
        print("\n正在连接示波器...")
        idn = scope.connect()
        print(f"设备：{idn}")
        scope.configure_acquisition()
        for channel in range(1, cfg.TOTAL_RF_CHANNELS + 1):
            attempt = 0
            while True:
                attempt += 1
                print(f"\n========== RF{channel} / "
                      f"{cfg.TOTAL_RF_CHANNELS} ==========")
                user_input = input(
                    f"请将 CH{cfg.RF_CHANNEL} 连接到 RF{channel}，"
                    "确认信号稳定后按 Enter 采集（q 退出）..."
                )
                if user_input.strip().lower() == "q":
                    print("校准已中止，已保存的波形不会删除。")
                    return
                # 1. 采集
                print("正在采集...")
                scope.acquire_single()
                # 2. 读取两路波形
                t1, v1 = scope.read_waveform(
                    cfg.REFERENCE_CHANNEL
                )
                t2, v2 = scope.read_waveform(
                    cfg.RF_CHANNEL
                )
                # 3. 检查时间轴
                if len(t1) != len(t2):
                    raise ValueError("两路波形长度不一致")
                dt = float(np.median(np.diff(t1)))
                tolerance = max(abs(dt) * 1e-6, 1e-15)
                if not np.allclose(
                    t1, t2, rtol=0, atol=tolerance
                ):
                    raise ValueError("两路时间轴不一致")
                sample_rate = 1.0 / dt
                # 4. 保存原始波形
                filename = (
                    f"RF{channel:02d}_try{attempt:02d}.npz"
                )
                output_path = output_dir / filename
                np.savez_compressed(
                    output_path,
                    time=t1,
                    reference_voltage=v1,
                    rf_voltage=v2,
                    frequency_hz=cfg.RF_FREQUENCY_HZ,
                    sample_rate_hz=sample_rate,
                    rf_channel_index=channel,
                    instrument_id=idn,
                )
                print(f"原始数据已保存：{filename}")
                print(f"采样率：{sample_rate / 1e9:.3f} GS/s")
                # 5. 检查采样率
                samples_per_cycle = (
                    sample_rate / cfg.RF_FREQUENCY_HZ
                )
                if samples_per_cycle < cfg.MIN_SAMPLES_PER_CYCLE:
                    print(
                        f"采样率不足：每周期 "
                        f"{samples_per_cycle:.2f} 个点"
                    )
                    print("请调整示波器设置后重新采集")
                    continue
                if sample_rate < cfg.TARGET_SAMPLE_RATE_HZ:
                    print("提醒：实际采样率低于目标采样率")
                # 6. 正弦拟合与相位计算
                result = analyze_two_channels(
                    t1, v1, v2, cfg.RF_FREQUENCY_HZ
                )
                ref = result["reference"]
                rf = result["rf"]
                print(f"参考信号 R²：{ref.r_squared:.6f}")
                print(f"RF 信号 R²：{rf.r_squared:.6f}")
                # 7. 拟合质量检查
                if not (
                    np.isfinite(ref.r_squared)
                    and np.isfinite(rf.r_squared)
                    and ref.r_squared >= cfg.MIN_FIT_R_SQUARED
                    and rf.r_squared >= cfg.MIN_FIT_R_SQUARED
                ):
                    print("拟合质量不足，请重新采集当前通道")
                    continue
                # 8. 记录本通道相位差
                delta = result["phase_difference_deg"]
                phase_differences.append(delta)
                fit_qualities.append(
                    (ref.r_squared, rf.r_squared)
                )
                print(f"RF{channel} 相位差：{delta:+.3f}°")
                break
        # ====================================
        # 八通道补偿计算
        # ====================================
        reference_phase = phase_differences[0]
        print("\n========== 最终校准结果 ==========")
        print("通道    原始相位差    FPGA补偿角度")
        csv_path = output_dir / "compensation.csv"
        with open(
            csv_path, "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                "RF_Channel",
                "Phase_vs_Reference_deg",
                "Phase_vs_RF1_deg",
                "FPGA_Compensation_deg",
                "R2_Reference",
                "R2_RF",
            ])
            for i, phase in enumerate(phase_differences):
                relative_phase = wrap_degrees(
                    phase - reference_phase
                )
                compensation = wrap_degrees(
                    -relative_phase
                )
                r2_ref, r2_rf = fit_qualities[i]
                writer.writerow([
                    i + 1,
                    phase,
                    relative_phase,
                    compensation,
                    r2_ref,
                    r2_rf,
                ])
                print(
                    f"RF{i+1:<3}  "
                    f"{phase:+9.3f}°    "
                    f"{compensation:+9.3f}°"
                )
        print(f"\n校准完成，结果保存在：{output_dir}")
        print(f"补偿表：{csv_path}")
    except Exception as exc:
        print(f"\n出错：{type(exc).__name__}: {exc}")
    finally:
        scope.close()
if __name__ == "__main__":
    main()
