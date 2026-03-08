#!/usr/bin/env python3
"""
API 接口測試腳本
用於測試 Security Platform 的所有 API 端點
"""

import json
import sys
import requests
from typing import Optional, Dict, Any

BASE_URL = "http://127.0.0.1:8000"
TEST_EMAIL = f"testuser{__import__('time').time()}@example.com"
TEST_PASSWORD = "testpass123"
TEST_NAME = "API測試用戶"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name: str):
    print(f"\n{Colors.BLUE}=== {name} ==={Colors.END}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def test_health_check():
    """測試健康檢查端點"""
    print_test("健康檢查")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"健康檢查成功: {data}")
            return True
        else:
            print_error(f"健康檢查失敗: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"健康檢查異常: {str(e)}")
        return False

def test_register(email: str, password: str, full_name: str) -> Optional[Dict]:
    """測試用戶註冊"""
    print_test("用戶註冊")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": full_name
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"註冊成功: {data.get('email')}")
            return data
        elif response.status_code == 400:
            error = response.json().get('detail', '未知錯誤')
            print_warning(f"註冊失敗（用戶可能已存在）: {error}")
            return None
        else:
            print_error(f"註冊失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"註冊異常: {str(e)}")
        return None

def test_login(email: str, password: str) -> Optional[str]:
    """測試用戶登錄"""
    print_test("用戶登錄")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "email": email,
                "password": password
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            if token:
                print_success(f"登錄成功，獲取到 token: {token[:50]}...")
                return token
            else:
                print_error("登錄成功但未獲取到 token")
                return None
        else:
            print_error(f"登錄失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"登錄異常: {str(e)}")
        return None

def test_get_me(token: str) -> Optional[Dict]:
    """測試獲取當前用戶信息"""
    print_test("獲取當前用戶信息")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"獲取用戶信息成功: {data.get('email')}")
            return data
        else:
            print_error(f"獲取用戶信息失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"獲取用戶信息異常: {str(e)}")
        return None

def test_list_credentials(token: str) -> Optional[list]:
    """測試列出憑證"""
    print_test("列出 API 憑證")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/credentials",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"獲取憑證列表成功: {len(data)} 個憑證")
            return data
        else:
            print_error(f"獲取憑證列表失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"獲取憑證列表異常: {str(e)}")
        return None

def test_list_tasks(token: str) -> Optional[list]:
    """測試列出任務"""
    print_test("列出任務")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"獲取任務列表成功: {len(data)} 個任務")
            return data
        else:
            print_error(f"獲取任務列表失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"獲取任務列表異常: {str(e)}")
        return None

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("Security Platform API 接口測試")
    print(f"{'='*60}{Colors.END}\n")
    
    # 測試健康檢查
    if not test_health_check():
        print_error("\n健康檢查失敗，請確認服務器正在運行")
        sys.exit(1)
    
    # 測試註冊（使用新郵箱）
    user = test_register(TEST_EMAIL, TEST_PASSWORD, TEST_NAME)
    
    # 如果註冊失敗，嘗試使用已存在的測試帳號
    test_email = TEST_EMAIL
    if user is None:
        print_warning("嘗試使用已存在的測試帳號: test@example.com")
        test_email = "test@example.com"
    
    # 測試登錄
    token = test_login(test_email, TEST_PASSWORD)
    
    if token is None:
        print_error("\n無法獲取認證 token，後續測試將跳過")
        sys.exit(1)
    
    # 測試需要認證的端點
    test_get_me(token)
    test_list_credentials(token)
    test_list_tasks(token)
    
    print(f"\n{Colors.GREEN}{'='*60}")
    print("測試完成！")
    print(f"{'='*60}{Colors.END}\n")
    
    print(f"\n{Colors.BLUE}提示：")
    print(f"1. 訪問 http://127.0.0.1:8000/docs 查看完整的 API 文檔")
    print(f"2. 訪問 http://127.0.0.1:8000/redoc 查看 ReDoc 格式的文檔")
    print(f"3. 使用獲取的 token 進行認證測試")
    print(f"   Authorization: Bearer {token[:50]}...{Colors.END}\n")

if __name__ == "__main__":
    main()

