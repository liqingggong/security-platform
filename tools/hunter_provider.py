from __future__ import annotations

import base64
import hashlib
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Optional

from app.services.interfaces import IAssetSearchProvider, SearchRecord


class HunterProvider(IAssetSearchProvider):
    """Hunter API 提供者實作"""

    BASE_URL = "https://hunter.qianxin.com/openApi"

    def __init__(self, api_key: str, timeout: int = 30, max_limit: int = 10000):
        # Hunter 只需要 API Key
        self.api_key = api_key
        
        # 配置重試策略：DNS 解析失敗、連接超時等網絡錯誤時重試
        retry_strategy = Retry(
            total=3,  # 總共重試 3 次
            backoff_factor=1,  # 重試間隔：1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP 狀態碼重試
            allowed_methods=["GET"],  # 只對 GET 請求重試
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def search(
        self,
        query: str,
        fields: List[str] = None,
        limit: int = 1000,
        page: int = 1,
    ) -> List[SearchRecord]:
        """
        搜尋 Hunter 資產

        Args:
            query: Hunter 查詢語法，例如 "domain=\"example.com\""
            fields: 要返回的欄位，預設為 ["ip", "port", "link", "product"]
            limit: 每頁返回數量（最大 100）
            page: 頁碼

        Returns:
            List[SearchRecord]: 搜尋結果列表
        """
        if fields is None:
            fields = ["ip", "port", "link", "product"]

        # Hunter API 參數 (官方要求以 URL Query 方式傳遞；POST/JSON 會得到 404)
        import logging
        search_b64 = base64.b64encode(query.encode()).decode()
        params = {
            "api-key": self.api_key,
            "search": search_b64,
            "page": page,
            "page_size": min(limit, 100),  # Hunter 單頁最多 100 條
            "is_web": "0",  # 0 全量資產；1 只查 Web 資產
        }
        logging.info(f"[Hunter Debug] Query: {query}, Search B64: {search_b64[:30]}...")
        logging.info(f"[Hunter Debug] API Key (masked): {self.api_key[:4]}...{self.api_key[-4:]}")

        # 手動重試機制：處理 DNS 解析失敗、連接超時、速率限制等網絡錯誤
        max_retries = 3
        retry_delay = 3  # 初始延遲 3 秒（更長的延遲以避免速率限制）

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/search",
                    params=params,
                    timeout=(10, 30)  # (連接超時, 讀取超時)
                )
                response.raise_for_status()
                data = response.json()

                # 檢查 Hunter API 返回的錯誤
                if data.get("code") != 200:
                    error_msg = data.get("message", "Unknown error")
                    logging.error(f"[Hunter Debug] API error: code={data.get('code')}, message={error_msg}")

                    # 401 認證錯誤：API Key 過期或無效
                    if data.get("code") == 401 or "令牌" in error_msg or "過期" in error_msg:
                        raise Exception(f"Hunter API 認證失敗: {error_msg}，請檢查 API Key 是否過期")

                    # 如果是速率限制錯誤，等待後重試
                    if "请求太多" in error_msg or "Too many requests" in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"Hunter API error: {error_msg}")

                # 檢查 API 返回的數據
                if data.get("code") != 200:
                    error_msg = data.get("message", "Unknown error")

                    # 如果是速率限制錯誤，等待後重試
                    if "请求太多" in error_msg or "Too many requests" in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"Hunter API error: {error_msg}")

                    # 其他錯誤直接返回空列表
                    return []

                break  # 成功則跳出重試循環
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                # DNS 解析失敗、連接超時等網絡錯誤：重試
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # 指數退避：3s, 6s, 12s
                    time.sleep(wait_time)
                    continue
                else:
                    # 最後一次重試失敗，拋出異常
                    raise Exception(f"Hunter API request failed after {max_retries} retries: {str(e)}")
            except requests.exceptions.RequestException as e:
                # 其他請求錯誤（如 HTTP 錯誤）不重試，直接拋出
                raise Exception(f"Hunter API request failed: {str(e)}")

        # 處理 API 響應
        if data is None or data.get("code") != 200:
            error_msg = data.get("message", "Unknown error") if data else "No response data"
            raise Exception(f"Hunter API error: {error_msg}")

        results = data.get("data", {}).get("arr", [])
        total_count = data.get("data", {}).get("total", 0)
        logging.info(f"[Hunter Debug] Response code: {data.get('code')}, Message: {data.get('message')}, Total: {total_count}")
        logging.info(f"[Hunter Debug] Results type: {type(results)}, count: {len(results) if isinstance(results, list) else 'N/A'}")
        # 打印完整响应用于调试
        print(f"[Hunter Debug] Full response (first 500 chars): {str(data)[:500]}")
        if not isinstance(results, list):
            logging.warning(f"[Hunter Debug] Results is not a list: {type(results)}")
            return []
        records = []

        for result in results:
            # Hunter 返回的數據結構
            # {
            #   "ip": "1.1.1.1",
            #   "port": 443,
            #   "domain": "example.com",
            #   "url": "https://example.com",
            #   "web_title": "Example",
            #   "component": ["nginx"] 或 [{"name": "nginx"}] 或混合
            #   ...
            # }
            ip = result.get("ip", "")
            port = result.get("port", 0)
            url = result.get("url", "")
            domain = result.get("domain", "")
            product_list = result.get("component", [])
            # 處理 component 欄位：可能是 List[str] 或 List[dict] 或混合
            product_items = []
            try:
                if isinstance(product_list, list):
                    for comp in product_list:
                        if isinstance(comp, dict):
                            # 如果是字典，嘗試提取 name 欄位
                            name = comp.get("name") or comp.get("value") or str(comp)
                            product_items.append(str(name))
                        elif isinstance(comp, str):
                            product_items.append(comp)
                        else:
                            # 其他類型（int, float等）轉為字符串
                            product_items.append(str(comp))
                elif product_list:
                    # 如果不是列表，直接轉為字符串
                    product_items.append(str(product_list))
                product_str = ",".join(product_items) if product_items else None
            except Exception as e:
                # 如果處理 component 時出錯，記錄並使用空值
                import logging
                logging.warning(f"Hunter component 處理錯誤: {e}, component={product_list}, result={result}")
                product_str = None

            # 構建完整的 link
            link = url if url else (f"http://{domain}:{port}" if domain and port else "")

            record = SearchRecord(
                ip=ip,
                port=int(port) if port else 0,
                link=link,
                product=product_str,
                raw=result,
            )
            records.append(record)

        return records

