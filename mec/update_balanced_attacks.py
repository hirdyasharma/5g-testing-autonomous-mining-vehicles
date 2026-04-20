from pathlib import Path
import json
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "mec_config.json").read_text(encoding="utf-8"))
BALANCE = CONFIG["dataset_balance"]
RNG = np.random.default_rng(CONFIG["training"]["random_state"])
TARGET_LABELS = BALANCE["labels"]
NUMERIC_RANGES = {key: tuple(values) for key, values in BALANCE["numeric_ranges"].items()}
INT_COLUMNS = BALANCE["int_columns"]


def clip(frame: pd.DataFrame) -> pd.DataFrame:
    for column, (low, high) in NUMERIC_RANGES.items():
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").clip(low, high)
    for column in INT_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").round().fillna(0).astype(int)
    return frame


def sample_rows(frame: pd.DataFrame, label: str, count: int, seed: int) -> pd.DataFrame:
    rows = frame[frame["label"] == label]
    return rows.sample(n=count, replace=len(rows) < count, random_state=seed).copy()


def build_synthetic(frame: pd.DataFrame, label: str, count: int, seed: int) -> pd.DataFrame:
    base_label = BALANCE["base_labels"][label]
    profile = BALANCE["synthetic_profiles"][label]
    rows = sample_rows(frame, base_label, count, seed)
    rows["label"] = label
    for field, spec in profile.items():
        if field in {"int_fields", "fixed_fields"}:
            continue
        rows[field] = RNG.normal(spec["mean"], spec["std"], count)
    for field, spec in profile.get("int_fields", {}).items():
        rows[field] = RNG.integers(spec[0], spec[1], count)
    for field, value in profile.get("fixed_fields", {}).items():
        rows[field] = value
    return clip(rows)


def rebuild_dataset(filename: str, base_seed: int) -> pd.DataFrame:
    frame = pd.read_csv(ROOT / filename)
    target_count = min(
        *(len(frame[frame["label"] == BALANCE["base_labels"][label]]) for label in TARGET_LABELS)
    )
    parts = [
        sample_rows(frame, label, target_count, base_seed + index)
        if label in frame["label"].values
        else build_synthetic(frame, label, target_count, base_seed + index)
        for index, label in enumerate(TARGET_LABELS, start=1)
    ]
    result = pd.concat(parts, ignore_index=True)
    result = result.sample(frac=1.0, random_state=base_seed + len(TARGET_LABELS) + 1).reset_index(drop=True)
    result.to_csv(ROOT / filename, index=False)
    return result


def main() -> None:
    train = rebuild_dataset("train.csv", BALANCE["train_seed"])
    test = rebuild_dataset("test.csv", BALANCE["test_seed"])
    print("train")
    print(train["label"].value_counts().to_string())
    print()
    print("test")
    print(test["label"].value_counts().to_string())


if __name__ == "__main__":
    main()
