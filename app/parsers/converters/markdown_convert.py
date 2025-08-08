from markitdown import MarkItDown
import pandas as pd

class MarkdownConverter:
    def __init__(self):
        self.md = MarkItDown(enable_plugins=False) 
        # pd.set_option('display.float_format', None)
        # pd.set_option('display.precision', 10)
    def markdown_convert(self, file_path: str) -> str:
        result = self.md.convert(file_path)
        return result.text_content
    def markdown_convert_manager(self, file_path: str) -> str:
        if file_path.endswith(".md"):
            return self.markdown_convert(file_path)
        else:
            raise ValueError("文件类型不支持")










