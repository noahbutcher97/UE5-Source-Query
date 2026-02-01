from typing import List, Dict, Any
import json

class ContextBuilder:
    """
    Constructs optimized context prompts from search results.
    Formats code snippets and definitions for LLM consumption.
    """
    
    def __init__(self, max_chars: int = 100000):
        self.max_chars = max_chars

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

        parts = ["<context>"]
        current_chars = len(parts[0])
        
        # 1. Add Definitions (High Priority)
        definitions = search_results.get('definition_results', [])
        for definition in definitions:
            # Extract content
            name = definition.get('entity_name', 'Unknown')
            file_path = definition.get('file_path', 'Unknown')
            content = definition.get('definition', '')
            
            if not content:
                continue
                
            entry = f"""
    <definition name="{name}" file="{file_path}">
{content}
    </definition>"""
            
            if current_chars + len(entry) > self.max_chars:
                break
                
            parts.append(entry)
            current_chars += len(entry)

        # 2. Add Semantic Hits (Medium Priority)
        # We need to fetch the actual text content if it's not in the result
        # The HybridQueryEngine results often just have 'path' and 'chunk_index'
        # We assume the caller might have hydrated them, or we accept what we have.
        # For now, let's assume we rely on definitions mostly, or snippets if provided.
        
        # Note: In the current architecture, semantic results from query() don't return full text 
        # unless we explicitly ask for it or re-read it. 
        # Ideally, the AssistantView should hydrate this before calling build_context, 
        # or we accept that we mainly feed definitions for now.
        
        parts.append("</context>")
        return "\n".join(parts)

    def format_system_prompt(self, base_prompt: str, context: str) -> str:
        """Combine base instruction with context"""
        if not context:
            return base_prompt
            
        return f"""{base_prompt}

You have access to the following relevant UE5 source code context:

{context}

Use this context to answer the user's question accurately. 
Cite specific member variables or functions from the provided code when applicable.
If the context doesn't contain the answer, rely on your general knowledge but mention that the specific code wasn't found."""
