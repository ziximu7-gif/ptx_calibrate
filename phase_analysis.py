
from dataclasses import dataclass
import numpy as np

@dataclass
class SineFitResult:
    """正弦拟合结果。"""
    phase_rad: float
    phase_deg: float
    amplitude: float
    offset: float
    r_squared: float
    residual_rms: float

def wrap_degrees(angle_deg: float) -> float:
    """将角度归一化到 [-180, 180)。"""
    return (float(angle_deg) + 180.0) % 360.0 - 180.0

def fit_sine_phase(
    t: np.ndarray,
    voltage: np.ndarray,
    frequency_hz: float,
) -> SineFitResult:
    """
    在已知频率下拟合正弦波。
    模型：
        y(t) = a*sin(2*pi*f*t) + b*cos(2*pi*f*t) + c
    相位：
        phase = atan2(b, a)
    t 的单位必须是秒，frequency_hz 的单位是 Hz。
    """
    t = np.asarray(t, dtype=float)
    voltage = np.asarray(voltage, dtype=float)
    if t.ndim != 1 or voltage.ndim != 1:
        raise ValueError("时间和电压必须是一维数组")
    if len(t) != len(voltage):
        raise ValueError("时间数组与电压数组长度不一致")
    if len(t) < 10:
        raise ValueError("采样点太少，无法可靠拟合")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(voltage)):
        raise ValueError("波形中存在 NaN 或无穷值")
    if frequency_hz <= 0:
        raise ValueError("频率必须大于 0")
    if np.any(np.diff(t) <= 0):
        raise ValueError("时间数组必须严格递增")
    # 使用相对时间
    tau = t - t[0]
    duration = tau[-1]
    cycles = frequency_hz * duration

    if cycles < 3:
        raise ValueError("记录长度不足，至少需要覆盖 3 个周期")

    omega_t = 2.0 * np.pi * frequency_hz * tau

    # y = a*sin(wt) + b*cos(wt) + c
    matrix = np.column_stack(
        [
            np.sin(omega_t),
            np.cos(omega_t),
            np.ones_like(tau),
        ]
    )
    coeff, _, _, _ = np.linalg.lstsq(
        matrix,
        voltage,
        rcond=None,
    )
    a, b, offset = coeff
    fitted = matrix @ coeff
    residual = voltage - fitted

    amplitude = float(np.hypot(a, b))
    phase_rad = float(np.arctan2(b, a))
    phase_deg = float(np.degrees(phase_rad))

    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((voltage - voltage.mean()) ** 2))

    if ss_tot > 0:
        r_squared = 1.0 - ss_res / ss_tot
    else:
        r_squared = float("nan")

    residual_rms = float(np.sqrt(np.mean(residual**2)))

    return SineFitResult(
        phase_rad=phase_rad,
        phase_deg=phase_deg,
        amplitude=amplitude,
        offset=float(offset),
        r_squared=r_squared,
        residual_rms=residual_rms,
    )

def analyze_two_channels(
    t: np.ndarray,
    reference_voltage: np.ndarray,
    rf_voltage: np.ndarray,
    frequency_hz: float,
) -> dict:
    """
    分析同一次示波器采集中的两路波形。
    reference_voltage：参考信号，通常接 CH1
    rf_voltage：当前 RF 通道信号，通常接 CH2

    相位差定义：
        delta = phase_rf - phase_reference
    """
    reference = fit_sine_phase(
        t,
        reference_voltage,
        frequency_hz,
    )
    rf = fit_sine_phase(
        t,
        rf_voltage,
        frequency_hz,
    )
    delta_deg = wrap_degrees(
        rf.phase_deg - reference.phase_deg
    )
    return {
        "reference": reference,
        "rf": rf,
        "phase_difference_deg": delta_deg,
    }
