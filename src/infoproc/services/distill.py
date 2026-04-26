from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from infoproc.config import APISettings
from infoproc.services.openai_client import OpenAICompatibleClient
from infoproc.services.prompts import load_prompt


SYSTEM_PROMPT = "你是一个知识蒸馏专家，擅长从文本中提取核心智慧。"


@dataclass(slots=True)
class _BaseLLMService:
    api_settings: APISettings
    prompt_name: str
    title_suffix: str

    def render(self, content: str, source_name: str) -> str:
        client = OpenAICompatibleClient(self.api_settings)
        prompt = load_prompt(self.prompt_name)
        result = client.chat(SYSTEM_PROMPT, f"{prompt}\n\n待处理文本:\n{content}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"# {source_name} - {self.title_suffix}\n\n生成时间：{timestamp}\n\n{result.strip()}\n"


class DistillService(_BaseLLMService):
    def __init__(self, api_settings: APISettings) -> None:
        super().__init__(api_settings, "distill.md", "四层知识框架")

    def write(self, content: str, source_name: str, output_path: Path) -> None:
        output_path.write_text(self.render(content, source_name), encoding="utf-8")


class RankService(_BaseLLMService):
    def __init__(self, api_settings: APISettings) -> None:
        super().__init__(api_settings, "rank.md", "ljg-rank 降秩总结")

    def write(self, content: str, source_name: str, output_path: Path) -> None:
        output_path.write_text(self.render(content, source_name), encoding="utf-8")
