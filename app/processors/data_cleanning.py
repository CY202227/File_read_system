"""
RAG数据清洗处理器
Data cleaning processor for RAG optimization
"""

from typing import Dict, Any, Optional, List
import time
import json

from config.logging_config import get_logger
from app.core.task_manager import task_manager as tm
from app.ai.client import AIClient
from app.api.schemas.file_cleaning_schemas import RAGMetadata
from app.processors.data_cleaning.prompt import (
    CONTENT_CLEANING_PROMPT,
    DIRECTORY_EXTRACTION_PROMPT,
    METADATA_GENERATION_PROMPT
)


class RAGDataCleaner:
    """RAG数据清洗处理器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.ai_client = AIClient()
        self.max_chunk_size = 18000  # 留出2000字缓冲，适应qwen3的2万字限制

    def clean_for_rag(self, task_id: str) -> Dict[str, Any]:
        """
        执行RAG数据清洗
        1. 读取文件内容
        2. 分块处理（考虑token限制）
        3. 清洗内容（移除引用、页眉页脚等）
        4. 提取目录
        5. 生成元数据

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        start_time = time.time()

        try:
            # 1. 获取任务配置
            task_doc = tm.get_task(task_id)
            request = task_doc.get("request", {})

            # 2. 读取文件内容
            self.logger.info("Reading file content for task_id=%s", task_id)
            file_content = self._read_file_content(task_id, request)

            if not file_content:
                raise ValueError("Failed to read file content")

            # 3. 分块处理内容
            self.logger.info("Splitting content into chunks for task_id=%s", task_id)
            content_chunks = self._split_content_into_chunks(file_content)

            # 4. 清洗每个块的内容
            self.logger.info("Cleaning content chunks for task_id=%s", task_id)
            cleaned_chunks = []
            for i, chunk in enumerate(content_chunks):
                self.logger.info("Processing chunk %d/%d", i+1, len(content_chunks))
                cleaned_chunk = self._clean_content_chunk(chunk)
                cleaned_chunks.append(cleaned_chunk)

            # 5. 合并清洗后的内容
            full_cleaned_content = "\n\n".join(cleaned_chunks)

            # 6. 提取目录
            self.logger.info("Extracting directory from content for task_id=%s", task_id)
            directory = self._extract_directory(full_cleaned_content)

            # 7. 生成元数据
            self.logger.info("Generating metadata for task_id=%s", task_id)
            metadata = self._generate_metadata(full_cleaned_content, directory)

            # 8. 计算处理时间
            processing_time = time.time() - start_time

            result = {
                "directory": directory,
                "content": full_cleaned_content,
                "metadata": metadata.model_dump() if metadata else None,
                "processing_time": processing_time
            }

            self.logger.info("RAG data cleaning completed for task_id=%s in %.2fs",
                           task_id, processing_time)
            return result

        except Exception as e:
            self.logger.error("RAG data cleaning failed for task_id=%s: %s", task_id, str(e))
            raise

    def _read_file_content(self, task_id: str, request: Dict[str, Any]) -> str:
        """读取文件内容"""
        from app.core.task_manager import TaskManager

        # 从任务文档的result中获取内容
        tm = TaskManager()
        try:
            task_doc = tm.get_task(task_id)
            self.logger.info("任务文档结构: %s", task_doc.keys())
            self.logger.info("任务状态: %s", task_doc.get("status"))

            result = task_doc.get("result", {})
            self.logger.info("result: %s", result)

            # 获取处理后的文本内容
            if result and isinstance(result, dict):
                data = result.get("data", {})
                self.logger.info("result.data: %s", data)
                if data and isinstance(data, dict):
                    # 直接获取文本内容
                    text_content = data.get("text", "")
                    self.logger.info("获取到的文本内容长度: %d", len(text_content))
                    if text_content:
                        self.logger.info("从任务result中获取到内容，长度: %d", len(text_content))
                        return text_content
                    else:
                        self.logger.warning("result.data.text为空")
                else:
                    self.logger.warning("result.data不是字典类型")
            else:
                self.logger.warning("result不存在或不是字典类型")

            # 尝试从process_json中获取
            process_json = task_doc.get("process_json", {})
            self.logger.info("process_json: %s", process_json)
            if process_json and isinstance(process_json, dict):
                text_content = process_json.get("text", "")
                self.logger.info("从process_json获取到的文本内容长度: %d", len(text_content))
                if text_content:
                    self.logger.info("从任务process_json中获取到内容，长度: %d", len(text_content))
                    return text_content

        except Exception as e:
            self.logger.error("从任务文档获取内容失败: %s", e)
            import traceback
            self.logger.error("详细错误信息: %s", traceback.format_exc())
            raise ValueError("无法从任务文档获取文件内容，请确保文件已正确处理")

        # 如果没有找到内容，返回空字符串
        self.logger.error("在任务文档中未找到任何文本内容")
        return ""

    def _split_content_into_chunks(self, content: str) -> List[str]:
        """将内容分块，考虑token限制"""
        if len(content) <= self.max_chunk_size:
            return [content]

        chunks = []
        current_chunk = ""

        # 按段落分割
        paragraphs = content.split('\n\n')

        for paragraph in paragraphs:
            # 如果添加这个段落会超过限制，先保存当前块
            if len(current_chunk + paragraph) > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _clean_content_chunk(self, chunk: str) -> str:
        """使用模型清洗单个内容块"""
        prompt = CONTENT_CLEANING_PROMPT.format(chunk=chunk)

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.ai_client.chat_invoke(
                messages=messages,
                temperature=0.1
            )

            # 清理响应中的多余内容
            cleaned_response = response.strip()
            if cleaned_response.startswith("清洗后的内容："):
                cleaned_response = cleaned_response[7:].strip()
            elif cleaned_response.startswith("以下是清洗后的内容："):
                cleaned_response = cleaned_response[10:].strip()

            return cleaned_response

        except Exception as e:
            self.logger.warning("Failed to clean content chunk with AI, returning original: %s", str(e))
            return chunk

    def _extract_directory(self, content: str) -> str:
        """从内容中提取目录"""
        # 如果内容太长，只取前一部分来提取目录
        content_sample = content[:10000] if len(content) > 10000 else content

        prompt = DIRECTORY_EXTRACTION_PROMPT.format(content_sample=content_sample)

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.ai_client.chat_invoke(
                messages=messages,
                max_tokens=2000,
                temperature=0.1
            )

            # 清理响应
            directory = response.strip()
            if directory.startswith("目录：") or directory.startswith("提取的目录："):
                directory = directory.split("：", 1)[1].strip()

            return directory

        except Exception as e:
            self.logger.warning("Failed to extract directory with AI: %s", str(e))
            return "无法提取目录"

    def _generate_metadata(self, content: str, directory: str) -> Optional[RAGMetadata]:
        """生成RAG元数据"""
        # 使用内容样本生成元数据（避免token超限）
        content_sample = content[:8000] if len(content) > 8000 else content

        prompt = METADATA_GENERATION_PROMPT.format(
            content_sample=content_sample,
            directory=directory
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.ai_client.chat_invoke(
                messages=messages,
            temperature=0.1
            )

            # 清理响应，提取JSON部分
            json_str = self._extract_json_from_response(response)

            if json_str:
                metadata_dict = json.loads(json_str)

                # 确保所有必需字段都存在
                required_fields = ['title', 'source_type', 'content_type', 'keywords',
                                 'main_topics', 'domain', 'chapter_titles']

                for field in required_fields:
                    if field not in metadata_dict:
                        if field in ['keywords', 'main_topics', 'chapter_titles']:
                            metadata_dict[field] = []
                        else:
                            metadata_dict[field] = f"未提取到{field}"

                # 添加content_length
                metadata_dict['content_length'] = len(content)

                return RAGMetadata(**metadata_dict)
            else:
                self.logger.warning("Failed to extract valid JSON from AI response")
                return None

        except Exception as e:
            self.logger.error("Failed to generate metadata: %s", str(e))
            return None

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """从AI响应中提取JSON部分"""
        import re

        # 查找JSON块
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)

        # 如果没找到，尝试查找```json块
        json_block_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1)

        return None


# 全局实例
rag_data_cleaner = RAGDataCleaner()


def clean_data_for_rag(task_id: str) -> Dict[str, Any]:
    """
    RAG数据清洗入口函数
    """
    return rag_data_cleaner.clean_for_rag(task_id)
