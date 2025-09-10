import os
import requests
import subprocess
from typing import Tuple
from config.settings import settings
import mimetypes
from config.logging_config import get_logger
import json
import functools
import inspect

logger = get_logger(__name__)

def _fc_build_log_message(func, bound: inspect.BoundArguments) -> str:
    keys = ["input_format", "target_format", "spilit_time", "file_path"]
    parts = []
    for k in keys:
        if k in bound.arguments:
            try:
                parts.append(f"{k}={bound.arguments.get(k)}")
            except Exception:
                parts.append(f"{k}=?")
    return ", ".join(parts)


def fc_log_call(func):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def _wrap(*args, **kwargs):
        try:
            bound = sig.bind_partial(*args, **kwargs)
        except Exception:
            bound = inspect.Signature().bind_partial()
        get_logger(__name__).info("enter %s(%s)", func.__qualname__, _fc_build_log_message(func, bound))
        return func(*args, **kwargs)
    return _wrap


class FileConverter:
    def __init__(self, ofd_authorization: str, ofd_clientid: str, file_path: str):
        self.ofd_authorization = ofd_authorization
        self.ofd_clientid = ofd_clientid
        if os.path.exists(file_path):
            self.file_path = file_path
        else:
            raise ValueError(f"文件不存在: {file_path}")

    @fc_log_call
    def run_convert(self, input_format: str, target_format: str) -> str:
        input_format = (input_format or "").lower()
        target_format = (target_format or "").lower()

        # ofd -> pdf（远端服务）
        if input_format == "ofd" and target_format in {"pdf", "auto"}:
            result, convert_result = self.ofd_wps_remote_convert()
        # wps -> docx（远端服务返回 docx）
        elif input_format == "wps" and target_format in {"pdf", "auto"}:
            result, convert_result = self.ofd_wps_remote_convert()
        # doc -> docx（本地 libreoffice）
        elif input_format == "doc" and target_format in {"docx", "auto"}:
            result, convert_result = self.doc_convert_to_docx()
        # xls -> xlsx（本地 libreoffice）
        elif input_format == "xls" and target_format in {"xlsx", "auto"}:
            result, convert_result = self.xls_convert_to_xlsx()
        # ppt -> pptx（本地 libreoffice）
        elif input_format == "ppt" and target_format in {"pptx", "auto"}:
            result, convert_result = self.ppt_convert_to_pptx()
        elif input_format == "audio_file" and target_format in {"text", "auto"}:
            result, convert_result = self.audio_file_convert_to_text(10)
        else:
            raise ValueError("文件类型或目标格式不支持")

        if result:
            return convert_result
        raise ValueError("转换失败")

    @fc_log_call
    def ofd_wps_remote_convert(self) -> Tuple[bool, str]:

        ofd_url = (settings.ofd_api_url or os.getenv("OFD_API_URL"))
        if not ofd_url:
            raise ValueError("OFD_API_URL环境变量未配置")

        headers = {
            "Authorization": self.ofd_authorization,
            "clientid": self.ofd_clientid
        }

        # 读取文件并上传
        filename = os.path.basename(self.file_path)
        with open(self.file_path, 'rb') as f:
            file_content = f.read()

        files = {"file": (filename, file_content, "application/octet-stream")}
        response = requests.post(ofd_url, headers=headers, files=files)
        response.raise_for_status()
        result_json = response.json()

        # 根据返回的数据结构获取realPath
        if result_json.get("code") == 200 and result_json.get("data"):
            real_path = result_json["data"].get("realPath")
            if real_path:
                if real_path.endswith(".wps"):
                    convert_path = real_path.replace(".wps", ".pdf")
                elif real_path.endswith(".ofd"):
                    convert_path = real_path.replace(".ofd", ".pdf")
                else:
                    convert_path = real_path
                return True, convert_path
            else:
                raise ValueError("获取文件路径失败")
        else:
            return False, str(result_json)
    @fc_log_call
    def doc_convert_to_docx(self) -> Tuple[bool, str]:
        output_path = self.file_path.replace(".doc", ".docx")
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to",
            "docx",
            self.file_path,
            "--outdir",
            os.path.dirname(self.file_path),
        ], check=False)
        return True, output_path


    @fc_log_call
    def xls_convert_to_xlsx(self) -> Tuple[bool, str]:
        output_path = self.file_path.replace(".xls", ".xlsx")
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to",
            "xlsx",
            self.file_path,
            "--outdir",
            os.path.dirname(self.file_path),
        ], check=False)
        return True, output_path


    @fc_log_call
    def ppt_convert_to_pptx(self) -> Tuple[bool, str]:
        output_path = self.file_path.replace(".ppt", ".pptx")
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to",
            "pptx",
            self.file_path,
            "--outdir",
            os.path.dirname(self.file_path),
        ], check=False)
        return True, output_path


    @fc_log_call
    def audio_file_convert_to_text(self, spilit_time) -> Tuple[bool, str]:
        """音频文件转换为文本"""
        from app.parsers.file_read.audio_read import AudioReader

        try:
            # 输出到 temp/temp_file 目录下，文件名与源音频同名
            stem = os.path.splitext(os.path.basename(self.file_path))[0]
            output_dir = os.path.join(settings.TEMP_DIR, "temp_file")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{stem}.txt")

            logger.info(f"Processing audio file: {self.file_path}")

            # 验证文件存在
            if not os.path.exists(self.file_path):
                raise ValueError(f"File not found at path: {self.file_path}")
            if not os.path.isfile(self.file_path):
                raise ValueError(f"Path is not a file: {self.file_path}")

            # 使用新的音频读取器
            reader = AudioReader()
            result = reader.read_audio(self.file_path)

            # 提取文本内容
            text_content = result.get('text', '')

            # 写入到输出文件
            with open(output_path, "w", encoding="utf-8") as out_fp:
                out_fp.write(text_content)

            logger.info(f"Audio conversion completed. Output saved to: {output_path}")
            return True, output_path

        except Exception as e:
            logger.exception(f"Unexpected error in audio_file_convert_to_text: {str(e)}")
            raise ValueError(f"Internal server error: {str(e)}")


