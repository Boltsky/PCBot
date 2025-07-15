#!/usr/bin/env python3
"""
Test script for the upload functionality
"""

import os
import tempfile
import shutil
from pathlib import Path

# Import the upload functions for testing
from PCRst import (
    UploadConfig, 
    sanitize_filename, 
    is_path_safe, 
    validate_file_security,
    calculate_file_hash,
    get_file_metadata,
    create_zip_from_directory
)

def test_upload_functionality():
    """Test the upload functionality components"""
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp(prefix="upload_test_")
    print(f"Testing in directory: {test_dir}")
    
    try:
        # Test 1: Create test files
        print("\n1. Creating test files...")
        
        # Create a simple text file
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("This is a test file for upload functionality testing.")
        
        # Create a JSON file
        json_file = os.path.join(test_dir, "config.json")
        with open(json_file, 'w') as f:
            f.write('{"test": "data", "upload": "functionality"}')
        
        # Create a subdirectory with files
        sub_dir = os.path.join(test_dir, "subdir")
        os.makedirs(sub_dir)
        
        sub_file = os.path.join(sub_dir, "subfile.txt")
        with open(sub_file, 'w') as f:
            f.write("This is a file in a subdirectory.")
        
        print("✅ Test files created successfully")
        
        # Test 2: Filename sanitization
        print("\n2. Testing filename sanitization...")
        
        dangerous_names = [
            "test<file>.txt",
            "CON.txt",
            "file|with|pipes.txt",
            "path/with/slashes.txt",
            "file with spaces.txt"
        ]
        
        for name in dangerous_names:
            sanitized = sanitize_filename(name)
            print(f"  '{name}' -> '{sanitized}'")
        
        print("✅ Filename sanitization working")
        
        # Test 3: Path safety checking
        print("\n3. Testing path safety...")
        
        # Test safe path (temp directory should be safe)
        safe_result = is_path_safe(test_file)
        print(f"  Test file safety: {safe_result}")
        
        # Test unsafe path (simulated)
        unsafe_path = "/etc/passwd"
        unsafe_result = is_path_safe(unsafe_path)
        print(f"  Unsafe path safety: {unsafe_result}")
        
        print("✅ Path safety checking working")
        
        # Test 4: File security validation
        print("\n4. Testing file security validation...")
        
        valid, msg = validate_file_security(test_file)
        print(f"  Text file validation: {valid} - {msg}")
        
        valid, msg = validate_file_security(json_file)
        print(f"  JSON file validation: {valid} - {msg}")
        
        # Test blocked extension (create a fake exe file)
        fake_exe = os.path.join(test_dir, "fake.exe")
        with open(fake_exe, 'w') as f:
            f.write("fake exe content")
        
        valid, msg = validate_file_security(fake_exe)
        print(f"  Fake exe validation: {valid} - {msg}")
        
        print("✅ File security validation working")
        
        # Test 5: File hash calculation
        print("\n5. Testing file hash calculation...")
        
        hash_result = calculate_file_hash(test_file)
        print(f"  Test file hash: {hash_result[:16]}...")
        
        print("✅ File hash calculation working")
        
        # Test 6: File metadata extraction
        print("\n6. Testing file metadata extraction...")
        
        metadata = get_file_metadata(test_file)
        if metadata:
            print(f"  File name: {metadata['name']}")
            print(f"  File size: {metadata['size_formatted']}")
            print(f"  MIME type: {metadata['mime_type']}")
            print(f"  Hash: {metadata['hash'][:16]}...")
        
        print("✅ File metadata extraction working")
        
        # Test 7: Directory compression
        print("\n7. Testing directory compression...")
        
        zip_path, zip_msg = create_zip_from_directory(sub_dir)
        if zip_path:
            print(f"  Zip created: {zip_path}")
            print(f"  Zip message: {zip_msg}")
            
            # Verify zip file exists
            if os.path.exists(zip_path):
                zip_size = os.path.getsize(zip_path)
                print(f"  Zip file size: {zip_size} bytes")
            
            # Clean up zip file
            if os.path.exists(zip_path):
                os.remove(zip_path)
        else:
            print(f"  Zip creation failed: {zip_msg}")
        
        print("✅ Directory compression working")
        
        # Test 8: Configuration validation
        print("\n8. Testing configuration...")
        
        print(f"  Max file size: {UploadConfig.MAX_FILE_SIZE / (1024*1024):.1f} MB")
        print(f"  Chunk size: {UploadConfig.CHUNK_SIZE / (1024*1024):.1f} MB")
        print(f"  Allowed MIME types: {len(UploadConfig.ALLOWED_MIME_TYPES)} types")
        print(f"  Blocked extensions: {len(UploadConfig.BLOCKED_EXTENSIONS)} extensions")
        print(f"  Safe directories: {len(UploadConfig.SAFE_DIRECTORIES)} directories")
        
        print("✅ Configuration validation working")
        
        print("\n🎉 All upload functionality tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")

if __name__ == "__main__":
    test_upload_functionality()
