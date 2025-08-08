import os
import requests
import subprocess
from typing import Tuple
from config.settings import settings
import mimetypes
from config.logging_config import get_logger
import json

logger = get_logger(__name__)

class FileConverter:
    def __init__(self, ofd_authorization: str, ofd_clientid: str, file_path: str):
        self.ofd_authorization = ofd_authorization
        self.ofd_clientid = ofd_clientid
        if os.path.exists(file_path):
            self.file_path = file_path
        else:
            raise ValueError(f"文件不存在: {file_path}")

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
        elif input_format == "audio_file" and target_format in {"text", "auto"}:
            result, convert_result = self.audio_file_convert_to_text(10)
        else:
            raise ValueError("文件类型或目标格式不支持")

        if result:
            return convert_result
        raise ValueError("转换失败")

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


    def audio_file_convert_to_text(self, spilit_time) -> Tuple[bool, str]:
        # 按照提供的唯一接口进行流式转写
        url = "http://180.153.21.76:12119/stream_audio_to_text" + f"?spilit_time={spilit_time}"
        headers = {"accept": "application/json"}
        files_payload = None

        try:
            # 输出到 temp/temp_file 目录下，文件名与源音频同名
            stem = os.path.splitext(os.path.basename(self.file_path))[0]
            output_dir = os.path.join(settings.TEMP_DIR, "temp_file")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{stem}.txt")
            logger.info(f"Processing local file path: {self.file_path}")
            if not os.path.exists(self.file_path):
                raise ValueError(f"File not found at path: {self.file_path}")
            if not os.path.isfile(self.file_path):
                raise ValueError(f"Path is not a file: {self.file_path}")

            filename = os.path.basename(self.file_path)
            guessed_type, _ = mimetypes.guess_type(self.file_path)
            content_type = guessed_type if guessed_type else "application/octet-stream"

            with open(self.file_path, 'rb') as f_local:
                file_content = f_local.read()
            files_payload = {"file": (filename, file_content, content_type)}
            logger.info(
                f"Sending request to {url} with file: {files_payload['file'][0] if files_payload['file'][0] else 'unnamed file'}"
            )

            response = requests.post(url, headers=headers, files=files_payload, stream=True)  # type: ignore
            response.raise_for_status()

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as out_fp:
                decoder = json.JSONDecoder()
                buffer = ""
                for chunk in response.iter_content(chunk_size=1024):
                    if not chunk:
                        continue
                    buffer += chunk.decode("utf-8", errors="ignore")
                    while True:
                        stripped = buffer.lstrip()
                        if not stripped:
                            buffer = ""
                            break
                        try:
                            obj, idx = decoder.raw_decode(stripped)
                        except json.JSONDecodeError:
                            # 需要更多数据
                            break
                        # 处理已完整解码的 JSON 对象
                        if isinstance(obj, dict):
                            text_piece = obj.get("text")
                            if isinstance(text_piece, str):
                                out_fp.write(text_piece)
                                out_fp.flush()
                        # 推进缓冲区
                        consumed = len(buffer) - len(stripped) + idx
                        buffer = buffer[consumed:]

            try:
                response.close()
            except Exception:
                pass

        except Exception as e:
            logger.exception(f"Unexpected error in audio_file_convert_to_text: {str(e)}")
            raise ValueError(f"Internal server error: {str(e)}")
        return True, output_path


