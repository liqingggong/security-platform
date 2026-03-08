from __future__ import annotations

import base64
import hashlib
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Optional
from datetime import datetime

from app.services.interfaces import IAssetSearchProvider, SearchRecord


class FofaProvider(IAssetSearchProvider):
    """FOFA API 提供者實作"""

    BASE_URL = "https://fofa.info/api/v1"

    def __init__(self, email: str, api_key: str):
        self.email = email
        self.api_key = api_key

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _generate_signature(self, query: str) -> str:
        sign_str = self.email + query + str(self.api_key)
        return base64.b64encode(hashlib.md5(sign_str.encode()).hexdigest().encode()).decode()

    def search(
        self,
        query: str,
        fields: List[str] = None,
        limit: int = 1000,
        page: int = 1,
        delay: float = 1.0,
    ) -> List[SearchRecord]:
        if fields is None:
            fields = ["ip", "port", "link", "product"]

        if delay > 0:
            time.sleep(delay)

        fields_str = ",".join(fields)

        sign = self._generate_signature(query)

        params = {
            "email": self.email,
            "key": self.api_key,
            "qbase64": base64.b64encode(query.encode()).decode(),
            "fields": fields_str,
            "size": min(limit, 10000),
            "page": page,
        }

        max_retries = 3
        retry_delay = 3  # 初始延遲 3 秒（更長的延遲以避免速率限制）

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/search/all",
                    params=params,
                    timeout=(10, 30)
                )
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.HTTPError as e:
                # 檢查是否是 429 錯誤
                if e.response is not None and e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 指數退避：3s, 6s, 12s
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"FOFA API rate limit exceeded after {max_retries} retries")
                else:
                    raise Exception(f"FOFA API request failed: {str(e)}")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"FOFA API request failed after {max_retries} retries: {str(e)}")
            except requests.exceptions.RequestException as e:
                raise Exception(f"FOFA API request failed: {str(e)}")

        if not data.get("error"):
            results = data.get("results", [])
            records = []

            for result in results:
                if len(result) >= len(fields):
                    record = SearchRecord(
                        ip=result[0] if len(result) > 0 else "",
                        port=int(result[1]) if len(result) > 1 and result[1].isdigit() else 0,
                        link=result[2] if len(result) > 2 else "",
                        product=result[3] if len(result) > 3 else None,
                        raw=dict(zip(fields, result)),
                    )
                    records.append(record)

            return records
        else:
            error_msg = data.get("errmsg", "Unknown error")
            raise Exception(f"FOFA API error: {error_msg}")
