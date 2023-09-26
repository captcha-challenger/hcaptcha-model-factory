# -*- coding: utf-8 -*-
# Time       : 2023/9/24 15:07
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Literal

import hcaptcha_challenger as solver


@dataclass
class ContinueLabeling:
    prompt: str
    images_dir: Path = field(default=Path)
    model_path: Path = field(default=Path)

    branch: Literal["local", "remote"] = "local"

    _images: List[Path] = field(default_factory=list)

    def __post_init__(self):
        self._images = [
            self.images_dir.joinpath(img_name)
            for img_name in os.listdir(self.images_dir)
            if img_name.endswith(".png")
        ]

        if not self.model_path or not self.model_path.exists():
            print("NOT Found Model_Path, switch to remote mode")
            self.branch = "remote"

    @classmethod
    def from_prompt(cls, prompt: str, images_dir: Path, model_path: Path | None = None, **kwargs):
        prompt = prompt.replace("_", " ")

        if not images_dir.exists():
            raise FileNotFoundError(f"NOT Found Images_dir - {images_dir=}")
        if model_path is not None and isinstance(model_path, Path) and not model_path.exists():
            raise FileNotFoundError(f"NOT Found Model_Path - {model_path}")

        return cls(prompt=prompt, images_dir=images_dir, model_path=model_path, **kwargs)

    def mkdir(self) -> Tuple[Path, Path]:
        __formats = ("%Y-%m-%d %H:%M:%S.%f", "%Y%m%d%H%M")
        now = datetime.strptime(str(datetime.now()), __formats[0]).strftime(__formats[1])
        yes_dir = self.images_dir.joinpath(now, "yes")
        bad_dir = self.images_dir.joinpath(now, "bad")
        yes_dir.mkdir(parents=True, exist_ok=True)
        bad_dir.mkdir(parents=True, exist_ok=True)

        return yes_dir, bad_dir

    def execute(self):
        if not self._images:
            sys.exit()

        if self.branch == "remote":
            solver.install(upgrade=True)
            model_path = None
        else:
            model_path = str(self.model_path)

        yes_dir, bad_dir = self.mkdir()

        classifier = solver.BinaryClassifier()
        results = classifier.execute(self.prompt, self._images, model_path)
        for i, result in enumerate(results):
            if result is True:
                shutil.move(self._images[i], yes_dir)
            elif result is False:
                shutil.move(self._images[i], bad_dir)

        if "win32" in sys.platform:
            os.startfile(self.images_dir)


def run(prompt: str, model_name: str | None = None):
    prompt = prompt.replace("_", " ")

    task_name = solver.prompt2task(prompt)

    project_dir = Path(__file__).parent.parent
    images_dir = project_dir.joinpath("database2309", task_name)

    name = model_name or task_name
    model_path = project_dir.joinpath("model", name, f"{name}.onnx")
    if not model_path.exists():
        cl = ContinueLabeling.from_prompt(prompt, images_dir)
    else:
        cl = ContinueLabeling.from_prompt(prompt, images_dir, model_path)
    cl.execute()


if __name__ == "__main__":
    run(prompt="industrial scene")
