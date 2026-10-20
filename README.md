本代码为ptx RF输出端相位矫正使用，连接示波器，型号为Tektronix MDO4104-6
使用pyvisa-py直接与示波器通讯

详细项目文档在本文件夹中的word文档中。
使用正弦函数，相位拟合算法为numpy.linalg.lstsq，其中有一个前提是计算使用的频率是已知且准确的（因此第二版可以先测量实际频率）
uv run python capture_once.py

1.连接示波器，在scope_controller.py中设置示波器ip，capture_once.py修改采集信号频率，如果需要修改触发电平，修改：scope.configure_acquisition(trigger_level=0.0)
2.输出持续正弦信号
3.uv run python capture_once.py
4.切换通道重复采集
