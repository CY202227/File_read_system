"""
音频文件读取模块
Audio file reading module for speech-to-text conversion
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
import requests

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class AudioReader:
    """音频文件读取器，负责调用音频转文本API"""

    def __init__(self):
        self.api_url = settings.AUDIO_API_URL
        self.timeout = 300  # 5分钟超时

    def get_supported_extensions(self) -> List[str]:
        """获取支持的音频文件扩展名"""
        return ["mp3", "wav", "flac", "mp4", "m4a"]

    def _prepare_audio_file(self, file_path: str) -> Dict[str, Any]:
        """准备音频文件数据用于API调用"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"音频文件不存在: {file_path}")

        # 读取文件内容
        with open(path, 'rb') as f:
            file_content = f.read()

        # 准备multipart/form-data
        files_payload = {
            "file": (path.name, file_content, self._get_mime_type(path.suffix))
        }

        return files_payload

    def _get_mime_type(self, extension: str) -> str:
        """根据文件扩展名获取MIME类型"""
        mime_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac',
            '.mp4': 'video/mp4',  # MP4视频也可能包含音频
            '.m4a': 'audio/mp4'
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')

    def _call_audio_api(self, files_payload: Dict[str, Any]) -> Dict[str, Any]:
        """调用音频转文本API"""
        try:
            logger.info(f"开始调用音频转文本API: {self.api_url}")

            response = requests.post(
                self.api_url,
                files=files_payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            # 解析响应
            response_data = response.json()
            logger.info(f"音频API响应数据类型: {type(response_data)}")

            if not isinstance(response_data, list) or len(response_data) == 0:
                raise HTTPException(
                    status_code=500,
                    detail="音频API返回的数据格式不正确"
                )

            return response_data[0]  # 返回第一个结果

        except requests.exceptions.Timeout:
            logger.error("音频API调用超时")
            raise HTTPException(status_code=504, detail="音频处理超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"音频API调用失败: {e}")
            raise HTTPException(status_code=500, detail=f"音频API调用失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"解析音频API响应失败: {e}")
            raise HTTPException(status_code=500, detail=f"解析API响应失败: {str(e)}")

    def _process_audio_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理音频API的返回结果，转换为系统需要的格式"""
        try:
            # 提取主要信息
            text = api_result.get('text', '')
            key = api_result.get('key', '')
            timestamp = api_result.get('timestamp', [])
            sentence_info = api_result.get('sentence_info', [])

            logger.info(f"音频转录完成，文本长度: {len(text)}，句子数量: {len(sentence_info)}")

            # 构建结构化结果
            processed_result = {
                'text': text,
                'key': key,
                'metadata': {
                    'audio_duration_ms': self._calculate_duration(timestamp),
                    'sentence_count': len(sentence_info),
                    'word_count': len(timestamp)
                },
                'sentences': sentence_info,
                'timestamps': timestamp
            }

            return processed_result

        except Exception as e:
            logger.error(f"处理音频结果失败: {e}")
            raise HTTPException(status_code=500, detail=f"处理音频结果失败: {str(e)}")

    def _calculate_duration(self, timestamp: List[List[int]]) -> Optional[int]:
        """计算音频总时长（毫秒）"""
        if not timestamp:
            return None

        # 找到最大结束时间
        max_end_time = max(end for _, end in timestamp) if timestamp else 0
        return max_end_time

    def read_audio(self, file_path: str) -> Dict[str, Any]:
        """
        读取音频文件并转换为文本

        Args:
            file_path: 音频文件路径

        Returns:
            Dict: 包含转录文本和元数据的字典
        """
        try:
            logger.info(f"开始处理音频文件: {file_path}")

            # 准备文件数据
            files_payload = self._prepare_audio_file(file_path)

            # 调用API
            api_result = self._call_audio_api(files_payload)

            # 处理结果
            processed_result = self._process_audio_result(api_result)

            logger.info(f"音频文件处理完成: {file_path}")
            return processed_result

        except Exception as e:
            logger.error(f"音频文件处理失败: {file_path}, 错误: {e}")
            raise


def read_audio(file_path: str, suffix: str) -> str:
    """
    读取音频文件并返回转录文本

    Args:
        file_path: 音频文件路径
        suffix: 文件扩展名

    Returns:
        str: 转录后的文本内容
    """
    reader = AudioReader()

    # 检查文件扩展名是否支持
    supported_extensions = reader.get_supported_extensions()
    if suffix.lstrip('.').lower() not in supported_extensions:
        raise ValueError(f"不支持的音频文件类型: {suffix}")

    # 检查是否已有转换后的文本文件
    from pathlib import Path
    text_path = Path(file_path).with_suffix('.txt')
    if text_path.exists():
        # 如果存在转换后的文本文件，直接读取
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"读取转换后的文本文件失败: {e}")

    # 否则重新进行音频转录
    result = reader.read_audio(file_path)

    # 返回纯文本内容
    return result.get('text', '')


def read_audio_with_metadata(file_path: str, suffix: str) -> Dict[str, Any]:
    """
    读取音频文件并返回包含元数据的完整结果

    Args:
        file_path: 音频文件路径
        suffix: 文件扩展名

    Returns:
        Dict: 包含文本、元数据、句子信息等的完整结果
    """
    reader = AudioReader()

    # 检查文件扩展名是否支持
    supported_extensions = reader.get_supported_extensions()
    if suffix.lstrip('.').lower() not in supported_extensions:
        raise ValueError(f"不支持的音频文件类型: {suffix}")

    # 读取并转录音频
    return reader.read_audio(file_path)
