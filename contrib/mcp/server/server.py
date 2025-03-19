# math_server.py
import math
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="MathServer", port=8080)

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract two numbers"""
    return a - b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    if b == 0:
        raise ValueError("Division by zero")
    return a / b

@mcp.tool()
def nth_root(a: float, b: float) -> float:
    """Compute the b-th root of a"""
    if b == 0:
        raise ValueError("Cannot take the 0th root")
    return math.pow(a, 1/b)

@mcp.tool()
def power(a: float, b: float) -> float:
    """Compute a raised to the power of b"""
    return math.pow(a, b)

@mcp.tool()
def modulo(a: float, b: float) -> float:
    """Compute a modulo b"""
    if b == 0:
        raise ValueError("Modulo by zero")
    return math.fmod(a, b)

@mcp.tool()
def log(a: float, b: float) -> float:
    """Compute the logarithm of a with base b"""
    if a <= 0 or b <= 0 or b == 1:
        raise ValueError("Invalid input for logarithm")
    return math.log(a) / math.log(b)

if __name__ == "__main__":
    mcp.run(transport="sse")
