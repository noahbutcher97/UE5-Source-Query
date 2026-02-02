from typing import List, Dict, Any
import json
from pathlib import Path

class ContextBuilder:
    """
    Constructs optimized context prompts from search results.
    Formats code snippets and definitions for LLM consumption.
    """
    
    def __init__(self, max_chars: int = 100000, prompt_dir: Path = None):
        self.max_chars = max_chars
        
        # Default to project_root/data/prompts if not provided
        if prompt_dir is None:
            # Assumes ue5_query/ai/context_builder.py -> project_root is 2 levels up (ue5_query/ai/../../)
            self.prompt_dir = Path(__file__).resolve().parents[2] / "data" / "prompts"
        else:
            self.prompt_dir = prompt_dir
            
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load templates from disk or fallback to defaults"""
        templates = {}
        # Define defaults in case files are missing (Safety fallback)
        defaults = {
            "rag_definition_entry.txt": '    <definition name="{name}" file="{file_path}">\n{content}\n    </definition>',
            "rag_context_wrapper.txt": '<context>\n{entries}\n</context>',
            "system_prompt_template.txt": '{base_prompt}\n\nYou have access to the following relevant UE5 source code context:\n\n{context}\n\nUse this context to answer the user\'s question accurately.'
        }
        
        for name, default_content in defaults.items():
            if self.prompt_dir:
                path = self.prompt_dir / name
                if path.exists():
                    try:
                        templates[name] = path.read_text(encoding='utf-8')
                        continue
                    except Exception:
                        pass
            templates[name] = default_content
        return templates

    def build_context(self, search_results: Dict[str, Any]) -> str:
        """
        Convert search results into a structured XML context string.
        
        Args:
            search_results: Output from HybridQueryEngine.query()
            
        Returns:
            String formatted as:
            <context>
                <definition name="FHitResult">...</definition>
                <code_snippet file="Actor.cpp">...</code_snippet>
            </context>
        """
        if not search_results:
            return ""

        entries = []
        current_chars = 0
        
        # 1. Add Definitions (High Priority)
        definitions = search_results.get('definition_results', [])
        for definition in definitions:
            # Extract content
            name = definition.get('entity_name', 'Unknown')
            file_path = definition.get('file_path', 'Unknown')
            content = definition.get('definition', '')
            
            if not content:
                continue
                
            entry = self.templates["rag_definition_entry.txt"].format(
                name=name,
                file_path=file_path,
                content=content
            )
            
            if current_chars + len(entry) > self.max_chars:
                break
                
            entries.append(entry)
            current_chars += len(entry)

        # 2. Add Semantic Hits (Medium Priority)
        # (Same logic as before - skipping for now as per original code)
        
        if not entries:
            return ""
            
        return self.templates["rag_context_wrapper.txt"].format(entries="\n".join(entries))

    def format_system_prompt(self, base_prompt: str, context: str) -> str:
        """Combine base instruction with context"""
        if not context:
            return base_prompt
            
        return self.templates["system_prompt_template.txt"].format(
            base_prompt=base_prompt,
            context=context
        )
