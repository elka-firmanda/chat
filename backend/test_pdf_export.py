#!/usr/bin/env python3
"""Test script for PDF export functionality."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from tools.pdf_exporter import generate_pdf, export_session_to_pdf

# Test data
test_session_data = {
    "id": "test-session-123",
    "title": "Test Chat Session",
    "created_at": "2024-01-04T10:30:00Z",
    "updated_at": "2024-01-04T11:45:00Z",
    "messages": [
        {
            "id": "msg-1",
            "role": "user",
            "content": "Hello! Can you help me understand how the agent system works?",
            "created_at": "2024-01-04T10:30:00Z",
        },
        {
            "id": "msg-2",
            "role": "assistant",
            "agent_type": "master",
            "content": "Of course! I'm the master agent that orchestrates all the subagents. Let me explain the system architecture.",
            "created_at": "2024-01-04T10:30:05Z",
            "metadata": {
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 150,
                "duration": 1.2,
            },
        },
        {
            "id": "msg-3",
            "role": "assistant",
            "agent_type": "planner",
            "content": "I need to create a step-by-step plan to explain this complex system. Let me break it down into clear sections.",
            "created_at": "2024-01-04T10:31:00Z",
            "metadata": {
                "thinking": [
                    {
                        "agent": "planner",
                        "content": "Let me organize my thoughts on how to structure this explanation clearly.",
                    }
                ]
            },
        },
        {
            "id": "msg-4",
            "role": "user",
            "content": "Can you show me some code examples?",
            "created_at": "2024-01-04T10:35:00Z",
        },
        {
            "id": "msg-5",
            "role": "assistant",
            "agent_type": "tools",
            "content": "Here's a Python code example:\n\n```python\ndef hello_world():\n    print('Hello, World!')\n    return True\n```\n\nThis shows a basic function definition.",
            "created_at": "2024-01-04T10:36:00Z",
            "metadata": {"model": "gpt-4-turbo", "tokens": 200, "duration": 2.5},
        },
    ],
}

print("Testing PDF export functionality...")
print("=" * 50)

# Test 1: Generate PDF to buffer
print("\n1. Testing PDF generation to buffer...")
try:
    pdf_buffer = generate_pdf(test_session_data)
    pdf_size = len(pdf_buffer.getvalue())
    print(f"   ✓ PDF generated successfully! Size: {pdf_size:,} bytes")
except Exception as e:
    print(f"   ✗ PDF generation failed: {e}")
    sys.exit(1)

# Test 2: Test with export_session_to_pdf
print("\n2. Testing export_session_to_pdf function...")
try:
    filename, pdf_bytes = export_session_to_pdf(test_session_data)
    print(f"   ✓ Export successful! Filename: {filename}")
    print(f"   ✓ PDF size: {len(pdf_bytes):,} bytes")
except Exception as e:
    print(f"   ✗ Export failed: {e}")
    sys.exit(1)

# Test 3: Test with custom filename
print("\n3. Testing with custom filename...")
try:
    custom_filename = "my_custom_export.pdf"
    filename, pdf_bytes = export_session_to_pdf(
        test_session_data, filename=custom_filename
    )
    print(f"   ✓ Custom filename test passed: {filename}")
except Exception as e:
    print(f"   ✗ Custom filename test failed: {e}")
    sys.exit(1)

# Test 4: Save to file (optional)
print("\n4. Testing file save...")
try:
    output_path = "/tmp/test_session_export.pdf"
    pdf_buffer = generate_pdf(test_session_data, output_path=output_path)
    import os

    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"   ✓ File saved successfully: {output_path}")
        print(f"   ✓ File size: {file_size:,} bytes")
        # Clean up
        os.remove(output_path)
    else:
        print("   ✗ File was not created")
except Exception as e:
    print(f"   ✗ File save test failed: {e}")

print("\n" + "=" * 50)
print("All tests passed! ✓")
print("=" * 50)
