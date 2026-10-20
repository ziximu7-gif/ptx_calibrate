import time
import numpy as np
import pyvisa
from config import VISA_ADDRESS, VISA_TIMEOUT_MS
class TektronixScope:
    def __init__(self, resource_name=VISA_ADDRESS):
        self.resource_name = resource_name
        self.rm = None
        self.scope = None
    def configure_acquisition(self, trigger_level=0.0):
        """配置连续正弦 RF 的单次采集。"""
        # 普通采样模式
        self.scope.write("ACQUIRE:MODE SAMPLE")
        # A 触发使用边沿触发
        self.scope.write("TRIGGER:A:TYPE EDGE")
        # CH1 作为参考触发源
        self.scope.write("TRIGGER:A:EDGE:SOURCE CH1")
        # 上升沿触发
        self.scope.write("TRIGGER:A:EDGE:SLOPE RISE")
        # 设置 CH1 触发电平，单位 V
        self.scope.write(
            f"TRIGGER:A:LEVEL:CH1 {trigger_level}"
        )
        # Normal：只在有效触发发生后采集
        self.scope.write("TRIGGER:A:MODE NORMAL")
        # 单次序列模式
        self.scope.write("ACQUIRE:STOPAFTER SEQUENCE")
    def connect(self):
        """连接示波器。"""
        self.rm = pyvisa.ResourceManager("@py")
        try:
            self.scope = self.rm.open_resource(
                self.resource_name
            )
            self.scope.timeout = 30000
            self.scope.write_termination = "\n"
            self.scope.read_termination = "\n"

            self.scope.write("HEADER OFF")

            return self.scope.query("*IDN?").strip()

        except Exception:
            self.close()
            raise
    def query(self, command):
        """读取 SCPI 查询结果。"""
        if self.scope is None:
            raise RuntimeError("示波器未连接")
        return self.scope.query(command).strip()
    def acquire_single(self, timeout_s=15):
        """
        启动一次单次序列采集，等待示波器停止。
        要求：
        - CH1 和 CH2 已连接
        - 信号已稳定
        - 触发源、触发电平已配置正确
        """
        if self.scope is None:
            raise RuntimeError("示波器未连接")

        # 使用普通采样模式
        self.scope.write("ACQUIRE:MODE SAMPLE")

        # 使用单次序列，保证两路波形属于同次采集
        self.scope.write("ACQUIRE:STOPAFTER SEQUENCE")

        # 启动新采集
        self.scope.write("ACQUIRE:STATE RUN")

        start = time.monotonic()

        while time.monotonic() - start < timeout_s:
            state = self.query("ACQUIRE:STATE?")
            count = int(float(self.query("ACQUIRE:NUMACQ?")))

            # 已停止，且确实完成至少一次采集
            if state in ("0", "OFF") and count > 0:
                return

            time.sleep(0.1)

        # 不读取可能属于旧采集的波形
        self.scope.write("ACQUIRE:STATE STOP")
        raise TimeoutError(
            "等待采集超时，请检查触发源和触发电平"
        )

    def read_waveform(self, channel, max_points=10000):
        """
        从已停止的采集记录读取指定模拟通道。

        返回：
            t: 时间数组，单位 s
            voltage: 电压数组，单位 V
        """
        if self.scope is None:
            raise RuntimeError("示波器未连接")

        if channel not in (1, 2, 3, 4):
            raise ValueError("通道必须是 1、2、3 或 4")

        if max_points < 10:
            raise ValueError("max_points 不能小于 10")

        # 选择输出通道
        self.scope.write(f"DATA:SOURCE CH{channel}")

        # 设置波形数据范围
        record_length = int(float(
            self.query("HORIZONTAL:RECORDLENGTH?")
        ))

        points = min(record_length, max_points)

        self.scope.write("DATA:START 1")
        self.scope.write(f"DATA:STOP {points}")

        # 有符号整数二进制格式，每点 2 字节
        self.scope.write("DATA:ENCDG RIBINARY")
        self.scope.write("DATA:WIDTH 2")

        # 读取波形的水平、垂直标定参数
        xincr = float(self.query("WFMOUTPRE:XINCR?"))
        xzero = float(self.query("WFMOUTPRE:XZERO?"))
        pt_off = float(self.query("WFMOUTPRE:PT_OFF?"))

        ymult = float(self.query("WFMOUTPRE:YMULT?"))
        yoff = float(self.query("WFMOUTPRE:YOFF?"))
        yzero = float(self.query("WFMOUTPRE:YZERO?"))

        byte_order = self.query("WFMOUTPRE:BYT_OR?").upper()

        if byte_order not in ("MSB", "LSB"):
            raise ValueError(
                f"无法识别的字节序: {byte_order}"
            )

        # 获取原始 ADC 波形数据
        raw = self.scope.query_binary_values(
            "CURVE?",
            datatype="h",
            is_big_endian=(byte_order == "MSB"),
            container=np.array,
        )

        if len(raw) != points:
            raise ValueError(
                f"波形点数不匹配：预期 {points}，实际 {len(raw)}"
            )

        # ADC 码转换成真实电压
        voltage = (raw - yoff) * ymult + yzero

        # 构造时间轴，DATA:START 为 1
        indices = np.arange(len(raw))
        t = xzero + (indices - pt_off) * xincr

        return t, voltage

    def close(self):
        """关闭 VISA 连接。"""
        if self.scope is not None:
            try:
                self.scope.close()
            finally:
                self.scope = None

        if self.rm is not None:
            try:
                self.rm.close()
            finally:
                self.rm = None
