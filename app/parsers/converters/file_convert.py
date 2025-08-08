import os
import requests
import subprocess
class FileConverter:
    def __init__(self, ofd_authorization: str, ofd_clientid: str,file_path: str):
        self.ofd_authorization = ofd_authorization
        self.ofd_clientid = ofd_clientid
        if os.path.exists(self.file_path):
            self.file_path = file_path
        else:
            raise ValueError(f"文件不存在: {self.file_path}")

    def file_convert_manager(self):

        if self.file_path.endswith(".ofd") or self.file_path.endswith(".wps"):
            result,convert_result = self.ofd_wps_convert()
        elif self.file_path.endswith(".doc"):
            result,convert_result = self.doc_convert()
        else:
            raise ValueError("文件类型不支持")
        if result:
            return convert_result
        else:
            raise ValueError("转换失败")
    def ofd_wps_convert(self):

        ofd_url = os.getenv("OFD_API_URL")
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
                    convert_path = real_path.replace(".wps",".docx")
                elif real_path.endswith(".ofd"):
                    convert_path = real_path.replace(".ofd",".pdf")
                return True,convert_path
            else:
                raise ValueError("获取文件路径失败")
        else:
            return False,result_json
    def doc_convert(self):
        output_path = self.file_path.replace(".doc", ".docx")
        subprocess.run(["libreoffice", "--headless", "--convert-to", "docx", self.file_path, "--outdir", os.path.dirname(self.file_path)])
        convert_path = output_path
        return True,convert_path






