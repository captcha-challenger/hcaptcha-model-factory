# -*- coding: utf-8 -*-
# Time       : 2023/10/24 5:39
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Tuple, List

from PIL import Image
from hcaptcha_challenger import (
    DataLake,
    install,
    ModelHub,
    ZeroShotImageClassifier,
    register_pipline,
)
from tqdm import tqdm

from flow_card import datalake_card

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s"
)

install(upgrade=True)


@dataclass
class AutoLabeling:
    """
    Example:
    ---

    1. Roughly observe the distribution of the dataset and design a DataLake for the challenge prompt.
        - ChallengePrompt: "Please click each image containing an off-road vehicle"
        - positive_labels --> ["off-road vehicle"]
        - negative_labels --> ["bicycle", "car"]

    2. You can design them in batches and save them as YAML files,
    which the classifier can read and automatically DataLake

    3. Note that positive_labels is a list, and you can specify multiple labels for this variable
    if the label pointed to by the prompt contains ambiguity。

    """

    input_dir: Path = field(default_factory=Path)
    pending_tasks: List[Path] = field(default_factory=list)
    tool: ZeroShotImageClassifier = field(default_factory=ZeroShotImageClassifier)

    output_dir: Path = field(default_factory=Path)

    limit: int = field(default=1)
    """
    By default, all pictures in the specified folder are classified and moved,
    Specifies the limit used to limit the number of images for the operation.
    """

    @classmethod
    def from_datalake(cls, dl: DataLake, **kwargs):
        if not isinstance(dl.joined_dirs, Path):
            raise TypeError(
                f"The dataset joined_dirs needs to be passed in for auto-labeling. - {dl.joined_dirs=}"
            )
        if not dl.joined_dirs.exists():
            raise ValueError(f"Specified dataset path does not exist - {dl.joined_dirs=}")

        input_dir = dl.joined_dirs
        pending_tasks = []
        for image_name in os.listdir(input_dir):
            image_path = input_dir.joinpath(image_name)
            if image_path.is_file():
                pending_tasks.append(image_path)

        if (limit := kwargs.get("limit")) is None:
            limit = len(pending_tasks)
        elif not isinstance(limit, int) or limit < 1:
            raise ValueError(f"limit should be a positive integer greater than zero. - {limit=}")

        tool = ZeroShotImageClassifier.from_datalake(dl)
        return cls(tool=tool, input_dir=input_dir, pending_tasks=pending_tasks, limit=limit)

    def mkdir(self) -> Tuple[Path, Path]:
        __formats = ("%Y-%m-%d %H:%M:%S.%f", "%Y%m%d%H%M")
        now = datetime.strptime(str(datetime.now()), __formats[0]).strftime(__formats[1])
        yes_dir = self.input_dir.joinpath(now, "yes")
        bad_dir = self.input_dir.joinpath(now, "bad")
        yes_dir.mkdir(parents=True, exist_ok=True)
        bad_dir.mkdir(parents=True, exist_ok=True)

        self.output_dir = yes_dir.parent

        return yes_dir, bad_dir

    def execute(self, model):
        if not self.pending_tasks:
            logging.info("No pending tasks")
            return

        yes_dir, bad_dir = self.mkdir()

        desc_in = f'"{self.input_dir.parent.name}/{self.input_dir.name}"'
        total = len(self.pending_tasks)

        logging.info(f"load {self.tool.positive_labels=}")
        logging.info(f"load {self.tool.candidate_labels=}")

        with tqdm(total=total, desc=f"Labeling | {desc_in}") as progress:
            for image_path in self.pending_tasks[: self.limit]:
                # The label at position 0 is the highest scoring target
                image = Image.open(image_path)
                results = self.tool(model, image)

                # we're only dealing with binary classification tasks here
                if results[0]["label"] in self.tool.positive_labels:
                    output_path = yes_dir.joinpath(image_path.name)
                else:
                    output_path = bad_dir.joinpath(image_path.name)

                shutil.move(image_path, output_path)

                progress.update(1)


def run():
    modelhub = ModelHub.from_github_repo()
    modelhub.parse_objects()

    model = register_pipline(modelhub)

    images_dir = Path(__file__).parent.parent.joinpath("database2309")

    for card in datalake_card:
        # Filter out the task cards we care about
        if "furniture" not in card["joined_dirs"]:
            continue
        # Generating a dataclass from serialized data
        dl = DataLake(
            positive_labels=card["positive_labels"],
            negative_labels=card["negative_labels"],
            joined_dirs=images_dir.joinpath(*card["joined_dirs"]),
        )
        # Starts an automatic labeling task
        al = AutoLabeling.from_datalake(dl)
        al.execute(model)
        # Automatically open output directory
        if "win32" in sys.platform and al.output_dir.is_dir():
            os.startfile(al.output_dir)


if __name__ == "__main__":
    run()
