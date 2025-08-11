from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

from config.logging_config import get_logger


logger = get_logger(__name__)


class ExcelRead:
    """将表格类文件读取为基础 DataFrame。

    支持：
    - .xlsx / .xlsm / .xltx / .xltm（使用 pandas.read_excel）
    - .csv（pandas.read_csv）
    - .tsv / .tab（pandas.read_csv，tab 分隔）
    """

    @staticmethod
    def dataframe_read(
        file_path: str,
        sheet: Union[int, str, None] = None
    ) -> Union[pd.DataFrame, list[dict]]:
        """读取文件为 DataFrame。

        Args:
            file_path: 文件路径
            sheet: 读取的工作表（仅对 Excel 有效）。默认读取所有表（None）。

        Returns:
            - serialize=False: pd.DataFrame 基础 DataFrame
            - serialize=True: list[dict] 记录列表（records），便于传输与还原
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        try:
            # Excel
            if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
                # 默认尽可能读取所有 sheet：当 sheet 为 None 时，pandas 返回 dict[str, DataFrame]
                data = pd.read_excel(file_path, sheet_name=sheet)
                if isinstance(data, dict):
                    if not data:
                        return []
                    frames = []
                    for sheet_name, frame in data.items():
                        f = frame.copy()
                        f["_sheet"] = sheet_name
                        frames.append(f)
                    df = pd.concat(frames, ignore_index=True, sort=False)
                else:
                    df = data

                # 确保可序列化（处理 NaN/日期等）
                df = df.where(pd.notnull(df), None)
                return df.to_dict(orient="records") 

            # CSV
            if suffix == ".csv":
                df = pd.read_csv(file_path)
                df = df.where(pd.notnull(df), None)
                return df.to_dict(orient="records")

            # TSV / TAB 分隔
            if suffix in {".tsv", ".tab"}:
                df = pd.read_csv(file_path, sep="\t")
                df = df.where(pd.notnull(df), None)
                return df.to_dict(orient="records")

            raise ValueError(f"不支持的文件类型（dataframe）：{suffix}")

        except Exception as exc:
            logger.error("读取表格为 DataFrame 失败: %s", exc)
            raise
