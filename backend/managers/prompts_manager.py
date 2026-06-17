import re
from typing import Dict, Any, Optional, Union, List
from ..storage.prompts_storage import PromptsStorage
from ..macros.macros_service import MacroService


class PromptsManager:
    def __init__(self, world_id: str):
        self.storage = PromptsStorage(world_id)
        self.macro_service = MacroService()

    def _process_block_value(self, value: Union[str, List[Dict[str, Any]], List[str]], default_context: Dict[str, Any]) -> str:
        """
        Process a block value, which may be a string or a list of items.
        Each item may have its own context.
        Returns a single string (concatenated with newlines if list).
        """
        if isinstance(value, str):
            return self.macro_service.apply(value, **default_context)
        elif isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    ctx = item.get("context", {})
                    # Use item's own context; no merging with default
                    parts.append(self.macro_service.apply(text, **ctx))
                else:
                    # item is a string
                    parts.append(self.macro_service.apply(str(item), **default_context))
            return "\n".join(parts)
        else:
            return str(value)

    def build_prompt(
            self, 
            prompt_type: str, 
            blocks: Dict[str, Dict[str, Any]],
            ) -> str:
        """
        Build prompt by applying macros to each block individually.
        Blocks can be:
        - simple string (with context)
        - list of strings (each with optional individual context)
        """
        template = self.storage.get_template(prompt_type)
        prompt_text = self.storage.get_prompt(prompt_type)
        if not template or not prompt_text:
            return ""

        # First pass: replace {{#if block}}...{{/if}} with either the block content (with {{block}} placeholder) or empty.
        pattern = r'\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}'

        def replace_conditional(match):
            block_name = match.group(1)
            block_content = match.group(2)
            if block_name in blocks and blocks[block_name].get("text"):
                # The content of the conditional may contain {{block_name}}, which will be replaced later.
                # We just return the block_content as is.
                return block_content
            return ""

        result = template
        prev = None
        while result != prev:
            prev = result
            result = re.sub(pattern, replace_conditional, result, flags=re.DOTALL)

        # Second pass: replace all {{block_name}} with processed block texts
        for block_name, block_data in blocks.items():
            block_value = block_data.get("text")
            if block_value:
                block_context = block_data.get("context", {})
                processed = self._process_block_value(block_value, block_context)
                result = result.replace(f"{{{{{block_name}}}}}", processed)

        final = result.strip()
        return final