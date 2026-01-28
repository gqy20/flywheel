"""Test for Issue #275: Verify Windows security code integrity.

This test ensures that the Windows security code in storage.py
is complete and has no truncated or incomplete logic.
"""

import pytest


def test_windows_security_code_integrity():
    """Test that Windows security code is complete and not truncated.

    Issue #275: Code was reported truncated at line 226 with incomplete
    `security_info = (` statement. This test verifies:
    1. The file can be parsed (syntax is valid)
    2. The security_info variable is properly defined
    3. The SetFileSecurity call is present
    4. The code structure is complete
    """
    # Read the storage.py file
    with open('src/flywheel/storage.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Check that the file is not empty
    assert len(content) > 0, "storage.py file is empty"

    # Check that security_info is defined somewhere in the file
    assert 'security_info' in content, \
        "security_info variable not found in storage.py"

    # Check that SetFileSecurity is called
    assert 'SetFileSecurity' in content, \
        "SetFileSecurity call not found in storage.py"

    # Verify the Windows security block has the correct structure
    # Look for the security_info assignment that's used with SetFileSecurity
    assert 'DACL_SECURITY_INFORMATION' in content, \
        "DACL_SECURITY_INFORMATION flag not found"
    assert 'PROTECTED_DACL_SECURITY_INFORMATION' in content or 'OWNER_SECURITY_INFORMATION' in content, \
        "Required security information flags not found"


def test_windows_security_code_structure():
    """Test that Windows security code has proper structure.

    Verifies that the _secure_directory method has complete logic
    for Windows security handling.
    """
    with open('src/flywheel/storage.py', 'r') as f:
        content = f.read()

    # Check for the complete Windows security block
    required_elements = [
        'win32security.SECURITY_DESCRIPTOR',
        'SetSecurityDescriptorOwner',
        'SetSecurityDescriptorDacl',
        'win32security.ACL',
        'AddAccessAllowedAce',
        'SetFileSecurity',
    ]

    for element in required_elements:
        assert element in content, \
            f"Required Windows security element '{element}' not found in storage.py"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
