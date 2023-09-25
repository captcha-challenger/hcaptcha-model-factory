# -*- coding: utf-8 -*-
# Time       : 2023/9/25 13:33
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import os
import zipfile
from pathlib import Path

import hcaptcha_challenger as solver


def zip_dataset(prompt: str):
    prompt = prompt.replace("_", " ")
    task_name = solver.prompt2task(prompt)

    project_dir = Path(__file__).parent.parent
    images_dir = project_dir.joinpath("database2309", task_name)

    zip_path = Path(f"{task_name}.zip")

    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for root, dirs, files in os.walk(images_dir):
            if root.endswith("yes"):
                for file in files:
                    zip_file.write(os.path.join(root, file), f"yes/{file}")
            elif root.endswith("bad"):
                for file in files:
                    zip_file.write(os.path.join(root, file), f"bad/{file}")

    print(f">> OUTPUT - {zip_path=}")


zip_dataset(prompt="robot")
