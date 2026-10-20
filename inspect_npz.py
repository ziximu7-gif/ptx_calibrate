import numpy as np
from pathlib import Path

file_path = Path("C:\\MuzixiFiles\\MRI\\ptx_calibrate\\20261020_205717_capture.npz")

with np.load(file_path, allow_pickle=False) as data:

    print("文件中的数据：")
    print("=" * 40)

    for key in data.files:
        arr = data[key]

        print(f"\n名称: {key}")
        print(f"形状: {arr.shape}")
        print(f"数据类型: {arr.dtype}")

        if arr.size > 0:
            print(f"前几个值: {arr.flat[:5]}")
