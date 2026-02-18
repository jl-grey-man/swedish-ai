"""Test LLM utilities."""
from phases.llm_utils import validate_schema
import pytest


def test_validate_schema_valid():
    """Test that valid data passes schema validation."""
    schema = {
        "required": ["name"],
        "properties": {"name": {"type": "string"}}
    }
    data = {"name": "test"}
    
    # Should not raise
    validate_schema(data, schema)


def test_validate_schema_missing_field():
    """Test that missing required field raises error."""
    schema = {
        "required": ["name"],
        "properties": {"name": {"type": "string"}}
    }
    data = {}
    
    with pytest.raises(ValueError, match="Missing required field"):
        validate_schema(data, schema)


def test_validate_schema_wrong_type():
    """Test that wrong type raises error."""
    schema = {
        "required": ["count"],
        "properties": {"count": {"type": "integer"}}
    }
    data = {"count": "not a number"}
    
    with pytest.raises(ValueError, match="expected int"):
        validate_schema(data, schema)


def test_validate_schema_nullable():
    """Test that nullable fields work correctly."""
    schema = {
        "required": ["optional_field"],
        "properties": {
            "optional_field": {"type": ["string", "null"]}
        }
    }
    
    # Null should be valid
    data = {"optional_field": None}
    validate_schema(data, schema)
    
    # String should be valid
    data = {"optional_field": "value"}
    validate_schema(data, schema)


def test_validate_schema_array():
    """Test array type validation."""
    schema = {
        "required": ["items"],
        "properties": {"items": {"type": "array"}}
    }
    data = {"items": [1, 2, 3]}
    
    # Should not raise
    validate_schema(data, schema)
    
    # Wrong type should raise
    data_wrong = {"items": "not a list"}
    with pytest.raises(ValueError, match="expected list"):
        validate_schema(data_wrong, schema)


def test_validate_schema_object():
    """Test object type validation."""
    schema = {
        "required": ["config"],
        "properties": {"config": {"type": "object"}}
    }
    data = {"config": {"key": "value"}}
    
    # Should not raise
    validate_schema(data, schema)
