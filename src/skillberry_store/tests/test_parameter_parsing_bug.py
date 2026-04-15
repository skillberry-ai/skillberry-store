# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Test for parameter parsing bug fix."""

import pytest
from skillberry_store.tools.anthropic.code_parser import parse_python_function


def test_parse_function_with_default_value_no_type():
    """Test parsing function with default values but no type annotations."""
    function_code = '''
def book_reservation(
    user_id: str,
    origin: str,
    destination: str,
    flight_type: str,
    cabin: str,
    flights: str,
    passengers: str,
    payment_methods: str,
    total_baggages: 0,
    nonfree_baggages: 0,
    insurance: str
):
    """
    Creates a flight reservation for a user with specified travel details.

    Parameters:
        user_id (str): Identifier of the user making the reservation.
        origin (str): Departure location.
        destination (str): Arrival location.
        flight_type (str): Type of flight (e.g., one-way, round-trip).
        cabin (str): Cabin class (e.g., economy, business).
        flights (str): Flight identifiers or details.
        passengers (str): Passenger information.
        payment_methods (str): Selected payment method(s).
        total_baggages (int): Total number of baggages.
        nonfree_baggages (int): Number of baggages requiring payment.
        insurance (str): Insurance option selected.

    Returns:
        dict: Reservation confirmation details.
    """
    return {}
'''
    
    description, params, returns = parse_python_function(function_code, 'book_reservation')
    
    # Verify description is extracted
    assert 'Creates a flight reservation' in description
    
    # Verify params structure
    assert params is not None
    assert params['type'] == 'object'
    assert 'properties' in params
    
    properties = params['properties']
    
    # Check that all parameters are present
    assert 'user_id' in properties
    assert 'origin' in properties
    assert 'destination' in properties
    assert 'flight_type' in properties
    assert 'cabin' in properties
    assert 'flights' in properties
    assert 'passengers' in properties
    assert 'payment_methods' in properties
    assert 'total_baggages' in properties
    assert 'nonfree_baggages' in properties
    assert 'insurance' in properties
    
    # Check that parameters with type annotations have correct types
    assert properties['user_id']['type'] == 'string'
    assert properties['origin']['type'] == 'string'
    assert properties['insurance']['type'] == 'string'
    
    # Check that parameters with default values but no type annotation are present
    # (they should default to 'string' type since no type info is available)
    assert 'total_baggages' in properties
    assert 'nonfree_baggages' in properties
    
    # Check required parameters (those without default values)
    assert 'required' in params
    required = params['required']
    
    # Parameters with type annotations and no defaults should be required
    assert 'user_id' in required
    assert 'origin' in required
    assert 'destination' in required
    assert 'flight_type' in required
    assert 'cabin' in required
    assert 'flights' in required
    assert 'passengers' in required
    assert 'payment_methods' in required
    assert 'insurance' in required
    
    # Parameters with default values should NOT be required
    assert 'total_baggages' not in required
    assert 'nonfree_baggages' not in required


def test_parse_function_with_proper_type_and_default():
    """Test parsing function with proper type annotations and default values."""
    function_code = '''
def example_function(
    required_param: str,
    optional_param: str = "default",
    optional_int: int = 42
):
    """Example function."""
    return None
'''
    
    description, params, returns = parse_python_function(function_code, 'example_function')
    
    assert params is not None
    properties = params['properties']
    
    # All parameters should be present
    assert 'required_param' in properties
    assert 'optional_param' in properties
    assert 'optional_int' in properties
    
    # Check types
    assert properties['required_param']['type'] == 'string'
    assert properties['optional_param']['type'] == 'string'
    assert properties['optional_int']['type'] == 'integer'
    
    # Check required
    required = params['required']
    assert 'required_param' in required
    assert 'optional_param' not in required
    assert 'optional_int' not in required


def test_parse_function_with_mixed_parameters():
    """Test parsing function with various parameter styles."""
    function_code = '''
def mixed_function(
    a: str,
    b: int = 10,
    c: 5,
    d="default",
    e: str = "value"
):
    """Mixed parameter styles."""
    return None
'''
    
    description, params, returns = parse_python_function(function_code, 'mixed_function')
    
    assert params is not None
    properties = params['properties']
    
    # All parameters should be present
    assert 'a' in properties
    assert 'b' in properties
    assert 'c' in properties
    assert 'd' in properties
    assert 'e' in properties
    
    # Check required (only 'a' has no default)
    required = params['required']
    assert 'a' in required
    assert 'b' not in required
    assert 'c' not in required
    assert 'd' not in required
    assert 'e' not in required

# Made with Bob
