#!/usr/bin/env python3
"""
Qwen3-32B Token Counter CLI/Module
Usage: python qwen_count.py "your text here"
       from qwen_count import count_qwen_tokens
"""

import argparse
import sys
from pathlib import Path
from typing import Union, List, Dict, Any
import warnings

try:
    from transformers import AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

MODEL_NAME = "Qwen/Qwen3-32B"
_tokenizer = None

def _get_tokenizer():
    """Lazy load tokenizer once."""
    global _tokenizer
    if _tokenizer is None and HAS_TRANSFORMERS:
        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME, 
            trust_remote_code=True,
            use_fast=True
        )
    return _tokenizer

def count_qwen_tokens(
    text: Union[str, List[Dict[str, str]]], 
    chat_format: bool = False
) -> int:
    """
    Count tokens for Qwen3-32B.
    
    Args:
        text: String or chat messages list [{"role": "user", "content": "..."}]
        chat_format: If True, apply Qwen chat template
    
    Returns:
        Token count
    """
    if not HAS_TRANSFORMERS:
        raise ImportError(
            "Install transformers: pip install transformers"
        )
    
    tokenizer = _get_tokenizer()
    if tokenizer is None:
        raise RuntimeError("Failed to load tokenizer")
    
    if chat_format and isinstance(text, list):
        # Apply chat template for accurate count
        formatted = tokenizer.apply_chat_template(
            text, 
            tokenize=False, 
            add_generation_prompt=True,
            enable_thinking=False  # Exclude thinking tokens for raw count
        )
        tokens = len(tokenizer.encode(formatted))
    else:
        # Raw text
        tokens = len(tokenizer.encode(str(text)))
    
    return tokens

def main():
    parser = argparse.ArgumentParser(
        description="Qwen3-32B token counter"
    )
    parser.add_argument(
        "text", 
        nargs="+", 
        help="Text to count (quotes for multi-word)"
    )
    parser.add_argument(
        "--chat", 
        action="store_true",
        help="Treat as chat messages JSON"
    )
    args = parser.parse_args()
    
    text_input = " ".join(args.text)
    
    try:
        if args.chat:
            import json
            messages = json.loads(text_input)
            count = count_qwen_tokens(messages, chat_format=True)
        else:
            count = count_qwen_tokens(text_input, chat_format=False)
        
        print(f"Qwen3-32B tokens: {count}")
        sys.exit(0)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Tip: pip install transformers", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
