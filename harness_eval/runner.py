"""
Agent runner interface and implementations:
- OfflineFixtureRunner: zero-key, deterministic replaying from realistic evaluation fixtures.
- LiveLLMRunner: executes live LLM calls (LiteLLM or OpenAI) with assembled harness context.
"""
from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Tuple

from harness_eval.metrics.cost import calculate_cost, count_tokens
from harness_eval.models import EvalTask, HarnessConfig


class AgentRunner(ABC):
    """
    Abstract interface for executing an agent task under a given harness.
    """

    @abstractmethod
    def run_task(
        self,
        task: EvalTask,
        harness: HarnessConfig,
    ) -> Tuple[Dict[str, str], int, int, float, Optional[str]]:
        """
        Executes the agent on the task.
        Returns:
            (generated_files_dict, input_tokens, output_tokens, duration_sec, error_msg)
        """
        pass


class OfflineFixtureRunner(AgentRunner):
    """
    Deterministic fixture runner that loads pre-recorded realistic agent outputs.
    Guarantees fast, offline, and reliable evaluation runs for CI and assessments.
    """

    def __init__(self, fixtures_dir: Path | str = "fixtures"):
        self.fixtures_dir = Path(fixtures_dir)

    def run_task(
        self,
        task: EvalTask,
        harness: HarnessConfig,
    ) -> Tuple[Dict[str, str], int, int, float, Optional[str]]:
        start_time = time.time()
        harness_key = harness.name.lower().replace(" ", "_")
        candidate_dirs = [
            self.fixtures_dir / harness_key / task.id,
            self.fixtures_dir / harness.name / task.id,
        ]
        if "baseline" in harness_key:
            candidate_dirs.append(self.fixtures_dir / "baseline" / task.id)
        if "v2" in harness_key or "candidate_v2" in harness_key:
            candidate_dirs.append(self.fixtures_dir / "candidate_v2" / task.id)
        if "regressive" in harness_key:
            candidate_dirs.append(self.fixtures_dir / "candidate_regressive" / task.id)

        task_fixture_dir = None
        for cdir in candidate_dirs:
            if cdir.exists():
                task_fixture_dir = cdir
                break

        if not task_fixture_dir:
            return {}, 0, 0, 0.0, f"No offline fixture found for harness '{harness.name}', task '{task.id}'"

        generated_files: Dict[str, str] = {}
        # Read all code files from fixture
        for file_path in task_fixture_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".meta.json"):
                rel_path = file_path.relative_to(task_fixture_dir).as_posix()
                generated_files[rel_path] = file_path.read_text(encoding="utf-8")

        # Read metadata if present
        meta_file = task_fixture_dir / ".meta.json"
        input_tokens = 0
        output_tokens = 0
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                input_tokens = meta.get("input_tokens", 0)
                output_tokens = meta.get("output_tokens", 0)
            except Exception:
                pass

        if input_tokens == 0:
            # Estimate based on prompt size
            assembled_prompt = assemble_harness_prompt(harness, task)
            input_tokens = count_tokens(assembled_prompt)
            output_code = "\n".join(generated_files.values())
            output_tokens = count_tokens(output_code)

        duration = round(time.time() - start_time + 0.15, 2)
        return generated_files, input_tokens, output_tokens, duration, None


class LiveLLMRunner(AgentRunner):
    """
    Live LLM runner that executes requests against real model APIs using LiteLLM/OpenAI.
    """

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def run_task(
        self,
        task: EvalTask,
        harness: HarnessConfig,
    ) -> Tuple[Dict[str, str], int, int, float, Optional[str]]:
        start_time = time.time()
        system_content = assemble_harness_prompt(harness, task)
        
        user_content = (
            f"TASK: {task.title}\n\n"
            f"REQUIREMENTS:\n{task.description}\n\n"
            f"STARTER FILES:\n"
        )
        for rel_path, code in task.starter_code.items():
            user_content += f"\nFile: {rel_path}\n```{code}```\n"

        user_content += (
            "\nPlease provide the complete, production-ready implementation of the solution. "
            "Output your code in markdown code blocks labeled with the file path (e.g. ```python:filename.py or ```python\n# File: filename.py)."
        )

        try:
            import litellm
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ]
            
            response = litellm.completion(
                model=harness.model or self.model,
                messages=messages,
                temperature=harness.temperature,
                max_tokens=2500,
            )
            
            content = response.choices[0].message.content or ""
            usage = response.usage
            in_tokens = getattr(usage, "prompt_tokens", count_tokens(system_content + user_content))
            out_tokens = getattr(usage, "completion_tokens", count_tokens(content))
            
            files = self._extract_files_from_markdown(content, task.expected_files)
            duration = round(time.time() - start_time, 2)
            return files, in_tokens, out_tokens, duration, None

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return {}, 0, 0, duration, f"Live LLM execution error: {str(e)}"

    def _extract_files_from_markdown(self, text: str, expected_files: list) -> Dict[str, str]:
        files: Dict[str, str] = {}
        # Pattern 1: ```python:path/to/file.py or ```python filename=path/to/file.py
        code_blocks = re.findall(r"```(?:python[:\s]+([\w\./\\_-]+))?\s*\n(.*?)```", text, re.DOTALL)
        for target_file, code in code_blocks:
            clean_code = code.strip()
            if target_file and target_file.strip():
                fname = target_file.strip()
                files[fname] = clean_code
            elif expected_files:
                # Default to primary expected file
                files[expected_files[0]] = clean_code
        if not files and expected_files:
            # Fallback: grab all text if no markdown block
            files[expected_files[0]] = text.strip()
        return files


def assemble_harness_prompt(harness: HarnessConfig, task: EvalTask) -> str:
    """
    Assembles the full harness context: AGENTS.md, rules, skills, and system prompt.
    """
    parts = []
    
    if harness.system_prompt:
        parts.append(harness.system_prompt)
        
    if harness.agents_md:
        parts.append(f"## PROJECT AGENTS GUIDE (AGENTS.md):\n{harness.agents_md}")
        
    if harness.rules:
        parts.append("## ACTIVE RULES & CONVENTIONS:")
        for rname, rcontent in harness.rules.items():
            parts.append(f"### Rule [{rname}]:\n{rcontent}")
            
    if harness.skills:
        parts.append("## AVAILABLE SKILLS & CAPABILITIES:")
        for sname, scontent in harness.skills.items():
            parts.append(f"### Skill [{sname}]:\n{scontent}")
            
    return "\n\n".join(parts)
