"""
LLM utilities with forced JSON schema validation.
All LLM calls go through here to ensure structured outputs.
"""

import anthropic
import json
import logging
import os
from typing import Dict, Any

log = logging.getLogger("llm")

def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Call Claude API with forced JSON response.
    
    Args:
        system_prompt: System instructions
        user_prompt: User message
        schema: JSON schema to validate against
        model: Claude model to use
        max_tokens: Max response tokens
        
    Returns:
        Parsed and validated JSON dict
        
    Raises:
        json.JSONDecodeError: If response is not valid JSON
        ValueError: If response doesn't match schema
    """
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0,  # Deterministic
            system=[
                {"type": "text", "text": system_prompt},
                {
                    "type": "text",
                    "text": f"You MUST respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}\n\nNo markdown, no explanation, ONLY the JSON object.",
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # Extract text
        response_text = response.content[0].text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        
        # Parse JSON
        data = json.loads(response_text)
        
        # Basic validation
        validate_schema(data, schema)
        
        log.info(f"LLM call successful: {model}")
        return data
        
    except json.JSONDecodeError as e:
        log.error(f"LLM returned invalid JSON: {e}")
        log.error(f"Response was: {response_text[:500]}")
        raise
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        raise


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]):
    """
    Basic schema validation - checks required fields exist and types match.
    For production, consider using jsonschema library.
    """
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Type checking for top-level fields
    properties = schema.get("properties", {})
    for field, value in data.items():
        if field in properties:
            expected_type = properties[field].get("type")
            if not expected_type:
                continue
                
            actual_type = type(value).__name__
            
            type_map = {
                "string": "str",
                "integer": "int",
                "number": ["int", "float"],
                "boolean": "bool",
                "array": "list",
                "object": "dict"
            }
            
            # Handle nullable types
            if isinstance(expected_type, list):
                if "null" in expected_type and value is None:
                    continue
                expected_type = [t for t in expected_type if t != "null"][0]

            expected = type_map.get(expected_type, expected_type)
            
            if isinstance(expected, list):
                if actual_type not in expected:
                    raise ValueError(
                        f"Field {field}: expected {expected}, got {actual_type}"
                    )
            elif expected and actual_type != expected:
                raise ValueError(
                    f"Field {field}: expected {expected}, got {actual_type}"
                )


if __name__ == "__main__":
    # Test (requires ANTHROPIC_API_KEY in environment)
    print("Testing LLM utils...")
    
    test_schema = {
        "type": "object",
        "required": ["test_field"],
        "properties": {
            "test_field": {"type": "string"}
        }
    }
    
    # Check if API key exists
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set, skipping API test")
        print("✓ Module imports successfully")
    else:
        try:
            result = call_llm_json(
                system_prompt="You are a test assistant.",
                user_prompt='Respond with JSON: {"test_field": "hello"}',
                schema=test_schema
            )
            print(f"✓ Test passed: {result}")
        except Exception as e:
            print(f"✗ Test failed: {e}")
