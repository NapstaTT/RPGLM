"""
Generation orchestrator for sequential LLM calls.
"""

import asyncio
import re
from typing import Dict, Any, Optional, List

from ..llm.llm_client import KoboldCppClient
from ..context.context_builder import ContextBuilder
from ..parsers.response_parser import ResponseParser
from ..managers.prompts_manager import PromptsManager
from ..storage.lorebook_storage import LorebookStorage
from ..storage.persona_storage import PersonaStorage


class GenerationOrchestrator:
    """
    Orchestrates narrator -> character(s) generation with retries and abort.
    """

    def __init__(
        self,
        llm_client: KoboldCppClient,
        context_builder: ContextBuilder,
        prompts_manager: PromptsManager,
        response_parser: ResponseParser,
        lorebook_storage: LorebookStorage,
        persona_storage: PersonaStorage,
        llm_settings: Dict[str, Any],
        max_retries: int = 1,
        max_blocks: int = 3,
    ):
        self.llm = llm_client
        self.context_builder = context_builder
        self.prompts_manager = prompts_manager
        self.parser = response_parser
        self.lorebook = lorebook_storage
        self.persona_storage = persona_storage
        self.llm_settings = llm_settings
        self.max_retries = max_retries
        self.max_blocks = max_blocks
        self._abort_event = asyncio.Event()
        self._character_names = []

    def abort(self) -> None:
        self._abort_event.set()
        asyncio.create_task(self.llm.abort())

    def _reset(self) -> None:
        self._abort_event.clear()
        self._character_names = []

    def _check_abort(self) -> bool:
        return self._abort_event.is_set()

    def _load_character_names(self) -> List[str]:
        chars = self.lorebook.get_collection("characters")
        return [c.get("name", "").strip() for c in chars if c.get("name")]

    async def _run_narrator(
        self,
        world_state: Dict[str, Any],
        persona: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Run narrator generation.
        Returns list of blocks (narrative and character starts).
        """
        # Get system prompt from prompts manager
        system_prompt = self.prompts_manager.storage.get_prompt("narrator")

        # Build context blocks
        blocks = self.context_builder.build_prompt(
            prompt_type="narrator",
            world_state=world_state,
            persona=persona,
            system_prompt=system_prompt,
        )
        

        # Build final prompt string
        current_prompt = self.prompts_manager.build_prompt("narrator", blocks)
        print(f"[Orchestrator] Narrator prompt length: {len(current_prompt)}")

        buffer = ""
        full_response = ""
        saved_blocks = []
        retries = 0
        done = False

        while not done and retries <= self.max_retries and not self._check_abort():
            buffer = ""
            parse_result = None
            generation_completed = False

            print(f"[Orchestrator] Narrator attempt {retries+1}")

            try:
                async for chunk in self.llm.generate_stream(current_prompt, self.llm_settings):
                    if self._check_abort() or done:
                        break
                    buffer += chunk
                    full_response += chunk

                    # Check for character mask **Name:**
                    if re.search(r'\*\*[^*]+:\*\*', buffer):
                        parse_result = self.parser.parse_narrator(
                            buffer,
                            character_names=self._character_names,
                            max_blocks=self.max_blocks,
                        )
                        if parse_result["status"] in ("invalid_character", "limit_exceeded"):
                            # Abort current generation, we'll retry or stop
                            await self.llm.abort()
                            done = True
                            break
                        elif parse_result["status"] == "complete":
                            # We have at least one complete block (character)
                            if any(b["type"] == "character" for b in parse_result["blocks"]):
                                await self.llm.abort()
                                done = True
                                break
                else:
                    generation_completed = True

            except Exception as e:
                print(f"[Orchestrator] narrator LLM error: {e}")
                break

            # If generation completed without interruption, parse final buffer
            if not self._check_abort() and not done and buffer.strip() and parse_result is None:
                parse_result = self.parser.parse_narrator(
                    buffer,
                    character_names=self._character_names,
                    max_blocks=self.max_blocks,
                )

            # Handle parse result
            if parse_result is None:
                if buffer.strip():
                    saved_blocks.append({"type": "narrative", "content": buffer.strip()})
                break

            if parse_result["status"] == "complete":
                for block in parse_result["blocks"]:
                    saved_blocks.append(block)
                buffer = ""
                if any(b["type"] == "character" for b in parse_result["blocks"]):
                    break
                continue

            if parse_result["status"] == "invalid_character":
                # Retry: cut off before invalid character tag
                trimmed = parse_result["text_before"] + "**"
                current_prompt = current_prompt + "\n\n[Continue from here]\n\n" + trimmed
                retries += 1
                buffer = ""
                continue

            if parse_result["status"] == "limit_exceeded":
                # Save what we have and stop
                for block in parse_result["blocks"]:
                    saved_blocks.append(block)
                buffer = ""
                break

            # Fallback
            break

        # FALLBACK: if no blocks but full_response has content, save it
        if not saved_blocks and full_response.strip():
            print(f"[Orchestrator] FALLBACK: saving full_response as narrative ({len(full_response)} chars)")
            saved_blocks.append({"type": "narrative", "content": full_response.strip()})
        elif buffer.strip() and not saved_blocks:
            print("[Orchestrator] Saving buffer as narrative")
            saved_blocks.append({"type": "narrative", "content": buffer.strip()})

        print(f"[Orchestrator] Narrator returning {len(saved_blocks)} blocks")
        return saved_blocks

    async def _run_character(
        self,
        character_name: str,
        world_state: Dict[str, Any],
        persona: Dict[str, Any],
        existing_content: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate response for a single character.
        If existing_content is provided, use it as the character's speech.
        Otherwise, call LLM.
        """
        saved_blocks = []

        # If we already have content from narrator, just return it
        if existing_content and existing_content.strip():
            saved_blocks.append({
                "type": "character",
                "name": character_name,
                "content": existing_content.strip(),
            })
            return saved_blocks

        # Get system prompt for character
        system_prompt = self.prompts_manager.storage.get_prompt("character")

        # Build context
        blocks = self.context_builder.build_prompt(
            prompt_type="character",
            world_state=world_state,
            persona=persona,
            system_prompt=system_prompt,
            extra_context={"character_name": character_name},
        )

        current_prompt = self.prompts_manager.build_prompt("character", blocks)

        buffer = ""
        retries = 0
        done = False

        while not done and retries <= self.max_retries and not self._check_abort():
            buffer = ""
            parse_result = None
            generation_completed = False

            try:
                async for chunk in self.llm.generate_stream(current_prompt, self.llm_settings):
                    if self._check_abort() or done:
                        break
                    buffer += chunk

                    # Check for stop marker or character switch
                    if re.search(r'\*\*[^*]+:\*\*', buffer):
                        parse_result = self.parser.parse_character(
                            buffer,
                            character_name=character_name,
                            character_names=self._character_names,
                            stop_marker="**narrative:**",
                        )
                        if parse_result["status"] in ("stop_marker_found", "invalid_character", "character_switch"):
                            await self.llm.abort()
                            done = True
                            break
                else:
                    generation_completed = True

            except Exception as e:
                print(f"[Orchestrator] character LLM error: {e}")
                break

            # Final parse if needed
            if not self._check_abort() and not done and buffer.strip() and parse_result is None:
                parse_result = self.parser.parse_character(
                    buffer,
                    character_name=character_name,
                    character_names=self._character_names,
                    stop_marker="**narrative:**",
                )

            if parse_result is None:
                if buffer.strip():
                    saved_blocks.append({
                        "type": "character",
                        "name": character_name,
                        "content": buffer.strip(),
                    })
                break

            if parse_result["status"] == "complete":
                if parse_result["content"]:
                    saved_blocks.append({
                        "type": "character",
                        "name": character_name,
                        "content": parse_result["content"],
                    })
                break

            if parse_result["status"] == "stop_marker_found":
                if parse_result["content"]:
                    saved_blocks.append({
                        "type": "character",
                        "name": character_name,
                        "content": parse_result["content"],
                    })
                break

            if parse_result["status"] == "character_switch":
                if parse_result["text_before"]:
                    saved_blocks.append({
                        "type": "character",
                        "name": character_name,
                        "content": parse_result["text_before"],
                    })
                break

            if parse_result["status"] == "invalid_character":
                trimmed = parse_result["text_before"] + "**"
                current_prompt = current_prompt + "\n\n[Continue from here]\n\n" + trimmed
                retries += 1
                buffer = ""
                continue

            # Fallback
            if buffer.strip():
                saved_blocks.append({
                    "type": "character",
                    "name": character_name,
                    "content": buffer.strip(),
                })
            break

        return saved_blocks

    async def run(
        self,
        user_message: str,
        world_state: Dict[str, Any],
        persona: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._reset()

        if persona is None:
            persona = self.persona_storage.get()

        self._character_names = self._load_character_names()

        # 1. Narrator phase – получаем блоки
        narrator_blocks = await self._run_narrator(world_state, persona)

        # 2. Сохраняем narrative блоки, character блоки собираем в очередь
        final_messages = []
        character_queue = []  # (name, existing_content)

        for block in narrator_blocks:
            if len(final_messages) >= self.max_blocks:
                break

            if block["type"] == "narrative":
                final_messages.append({
                    "role": "narrator",
                    "content": block["content"],
                    "world_state": world_state,
                })
            elif block["type"] == "character":
                # Не сохраняем, только запоминаем для character-фазы
                character_queue.append({
                    "name": block["name"],
                    "content": block.get("content", ""),
                })

        # 3. Character phase – для каждого персонажа генерируем ответ (переключаем контекст)
        for char_info in character_queue:
            if len(final_messages) >= self.max_blocks:
                break

            # Вызываем character-генерацию (с переключением контекста)
            char_msgs = await self._run_character(
                character_name=char_info["name"],
                world_state=world_state,
                persona=persona,
                existing_content=char_info["content"],
            )

            for msg in char_msgs:
                if len(final_messages) >= self.max_blocks:
                    break
                final_messages.append({
                    "role": msg["name"],
                    "content": msg["content"],
                    "world_state": world_state,
                })

        return final_messages