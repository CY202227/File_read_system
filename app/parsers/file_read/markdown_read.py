from markitdown import MarkItDown

class MarkdownRead:
    def __init__(self):
        self.md = MarkItDown(enable_plugins=False)
    def markdown_convert(self, file_path: str) -> str:
        result = self.md.convert(file_path)
        return result.text_content or ""
    def markdown_convert_manager(self, file_path: str) -> str:
        return self.markdown_convert(file_path)










