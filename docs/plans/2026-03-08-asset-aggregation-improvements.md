# 资产聚合与展示优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 解决资产聚合和资产展示页面的4个主要问题：重复域名聚合不彻底、CDN域名未关联、指纹信息缺失严重、协议识别缺失

**Architecture:** 基于现有 FastAPI + SQLAlchemy + React/Ant Design 架构，通过新增聚合服务、CDN识别模块、协议推断器和指纹增强器来改善资产质量。使用 TDD 开发模式，每个功能先写测试后实现。

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy, PostgreSQL/SQLite, React, TypeScript, pytest

---

## 验收标准汇总

| 问题 | 当前状态 | 目标 | 验收指标 |
|------|----------|------|----------|
| 重复域名聚合 | 24个域名重复 | 同一(domain,ip,port)只保留一条 | 重复率<5% |
| CDN域名关联 | 17条CDN域名未关联 | 自动识别并关联原始域名 | CDN识别率>90% |
| 指纹信息缺失 | 63.8%缺失 | 提升至<30%缺失 | 指纹覆盖率>70% |
| 协议识别缺失 | 37.6%缺失 | 基于端口自动推断 | 协议识别率>95% |

---

## Task 1: 创建协议推断服务 (Protocol Inference Service)

**背景:** 37.6%的资产缺少协议信息，需要基于端口号自动推断 http/https

**Files:**
- Create: `app/services/protocol_inference.py`
- Create: `tests/services/test_protocol_inference.py`

### Step 1: 编写协议推断服务的测试

```python
# tests/services/test_protocol_inference.py
import pytest
from app.services.protocol_inference import ProtocolInferenceService, infer_protocol_from_port


def test_infer_protocol_from_common_ports():
    """测试常见端口的协议推断"""
    assert infer_protocol_from_port(80) == "http"
    assert infer_protocol_from_port(443) == "https"
    assert infer_protocol_from_port(8080) == "http"
    assert infer_protocol_from_port(8443) == "https"


def test_infer_protocol_from_https_ports():
    """测试HTTPS常用端口"""
    https_ports = [443, 8443, 9443, 10443, 4433]
    for port in https_ports:
        assert infer_protocol_from_port(port) == "https"


def test_infer_protocol_from_http_ports():
    """测试HTTP常用端口"""
    http_ports = [80, 8080, 8000, 8888, 9000, 3000, 5000, 8008]
    for port in http_ports:
        assert infer_protocol_from_port(port) == "http"


def test_infer_protocol_unknown_port():
    """测试未知端口返回None"""
    assert infer_protocol_from_port(12345) is None
    assert infer_protocol_from_port(None) is None


def test_infer_protocol_from_banner():
    """测试从banner推断协议"""
    service = ProtocolInferenceService()

    https_banner = "Server: nginx/1.18.0\nLocation: https://example.com"
    assert service.infer_from_banner(https_banner) == "https"

    http_banner = "HTTP/1.1 200 OK\nServer: Apache/2.4.41"
    assert service.infer_from_banner(http_banner) == "http"


def test_enhance_asset_protocol():
    """测试增强资产协议信息"""
    service = ProtocolInferenceService()

    # 有端口无协议的情况
    asset = {"port": 443, "protocol": None}
    result = service.enhance_asset(asset)
    assert result["protocol"] == "https"

    # 已有协议的情况（不覆盖）
    asset = {"port": 8080, "protocol": "https"}
    result = service.enhance_asset(asset)
    assert result["protocol"] == "https"

    # 从banner推断
    asset = {"port": 8443, "protocol": None, "banner": "HTTPS/1.1 200 OK"}
    result = service.enhance_asset(asset)
    assert result["protocol"] == "https"
```

**Step 2: 运行测试确认失败**

```bash
cd /Users/liqinggong/Documents/Information_gathering_and_scanning_tools/security_platform
python -m pytest tests/services/test_protocol_inference.py -v
```

**Expected:** FAIL with "ModuleNotFoundError: No module named 'app.services.protocol_inference'"

**Step 3: 实现协议推断服务**

```python
# app/services/protocol_inference.py
"""协议推断服务 - 基于端口和banner推断协议类型"""
from typing import Optional, Dict, Any

# 常见端口到协议的映射
PORT_PROTOCOL_MAP = {
    # HTTP ports
    80: "http",
    8080: "http",
    8000: "http",
    8888: "http",
    9000: "http",
    3000: "http",
    5000: "http",
    8008: "http",
    8081: "http",
    8082: "http",
    8083: "http",
    9090: "http",
    9093: "http",
    # HTTPS ports
    443: "https",
    8443: "https",
    9443: "https",
    10443: "https",
    4433: "https",
    2083: "https",
    2087: "https",
    2096: "https",
}

# Banner中指示HTTPS的关键词
HTTPS_INDICATORS = [
    "https://",
    "HTTPS",
    "TLS",
    "SSL",
    "certificate",
    "handshake",
]

# Banner中指示HTTP的关键词
HTTP_INDICATORS = [
    "HTTP/1.1",
    "HTTP/1.0",
    "HTTP/2",
]


def infer_protocol_from_port(port: Optional[int]) -> Optional[str]:
    """
    基于端口号推断协议类型

    Args:
        port: 端口号

    Returns:
        "http", "https" 或 None
    """
    if port is None:
        return None
    return PORT_PROTOCOL_MAP.get(port)


class ProtocolInferenceService:
    """协议推断服务"""

    def infer_from_banner(self, banner: Optional[str]) -> Optional[str]:
        """
        从服务banner中推断协议

        Args:
            banner: 服务响应banner

        Returns:
            "http", "https" 或 None
        """
        if not banner:
            return None

        banner_upper = banner.upper()

        # 优先检查HTTPS指示器（更安全）
        for indicator in HTTPS_INDICATORS:
            if indicator.upper() in banner_upper:
                return "https"

        # 检查HTTP指示器
        for indicator in HTTP_INDICATORS:
            if indicator in banner:
                return "http"

        return None

    def enhance_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强资产数据，填充缺失的协议信息

        Args:
            asset: 资产字典，包含 port, protocol, banner 等字段

        Returns:
            增强后的资产字典
        """
        result = asset.copy()

        # 如果已有协议，不覆盖
        if result.get("protocol"):
            return result

        # 尝试从端口推断
        port = result.get("port")
        protocol_from_port = infer_protocol_from_port(port)
        if protocol_from_port:
            result["protocol"] = protocol_from_port
            return result

        # 尝试从banner推断
        banner = result.get("banner") or result.get("data", {}).get("banner")
        if isinstance(banner, str):
            protocol_from_banner = self.infer_from_banner(banner)
            if protocol_from_banner:
                result["protocol"] = protocol_from_banner

        return result

    def batch_enhance(self, assets: list) -> list:
        """
        批量增强资产列表

        Args:
            assets: 资产字典列表

        Returns:
            增强后的资产列表
        """
        return [self.enhance_asset(asset) for asset in assets]
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/services/test_protocol_inference.py -v
```

**Expected:** All tests PASS

**Step 5: Commit**

```bash
git add tests/services/test_protocol_inference.py app/services/protocol_inference.py
git commit -m "feat: add protocol inference service for auto-detecting http/https from ports"
```

---

## Task 2: 创建CDN识别与关联服务

**背景:** 17条CDN域名（如 `*.cdn.cloudflare.net`）未与原始域名建立关联

**Files:**
- Create: `app/services/cdn_detector.py`
- Create: `tests/services/test_cdn_detector.py`
- Modify: `app/db/models.py` (添加CDN关联字段)

### Step 1: 编写CDN识别服务的测试

```python
# tests/services/test_cdn_detector.py
import pytest
from app.services.cdn_detector import CDNDetectorService, CDN_PATTERN_MAP


def test_detect_cloudflare_cdn():
    """测试识别Cloudflare CDN域名"""
    service = CDNDetectorService()

    assert service.detect_cdn("api.example.com.cdn.cloudflare.net") == "cloudflare"
    assert service.detect_cdn("static.site.com.cloudflare.net") == "cloudflare"
    assert service.detect_cdn("example.cloudflare-dns.com") == "cloudflare"


def test_detect_aliyun_cdn():
    """测试识别阿里云CDN"""
    service = CDNDetectorService()

    assert service.detect_cdn("static.example.com.w.kunlunar.com") == "aliyun"
    assert service.detect_cdn("img.site.com.w.alikunlun.net") == "aliyun"


def test_detect_tencent_cdn():
    """测试识别腾讯云CDN"""
    service = CDNDetectorService()

    assert service.detect_cdn("cdn.example.com.tc.cdn") == "tencent"


def test_no_cdn_detected():
    """测试非CDN域名"""
    service = CDNDetectorService()

    assert service.detect_cdn("api.example.com") is None
    assert service.detect_cdn("www.site.org") is None
    assert service.detect_cdn("internal.local") is None


def test_extract_original_domain_from_cdn():
    """测试从CDN域名提取原始域名"""
    service = CDNDetectorService()

    # Cloudflare
    assert service.extract_original_domain("api.fofa.info.cdn.cloudflare.net") == "api.fofa.info"
    assert service.extract_original_domain("static.example.com.cloudflare.net") == "static.example.com"

    # 非CDN域名返回原值
    assert service.extract_original_domain("api.example.com") == "api.example.com"


def test_normalize_cdn_domain():
    """测试CDN域名标准化"""
    service = CDNDetectorService()

    result = service.normalize_cdn_domain("api.fofa.info.cdn.cloudflare.net")
    assert result["is_cdn"] is True
    assert result["cdn_provider"] == "cloudflare"
    assert result["original_domain"] == "api.fofa.info"
    assert result["cdn_domain"] == "api.fofa.info.cdn.cloudflare.net"


def test_batch_process_domains():
    """测试批量处理域名列表"""
    service = CDNDetectorService()

    domains = [
        "api.example.com",
        "static.example.com.cdn.cloudflare.net",
        "www.test.com",
        "img.test.com.w.kunlunar.com",
    ]

    results = service.batch_process(domains)

    assert len(results) == 4
    assert results[0]["is_cdn"] is False
    assert results[1]["is_cdn"] is True
    assert results[1]["cdn_provider"] == "cloudflare"
    assert results[3]["cdn_provider"] == "aliyun"
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest tests/services/test_cdn_detector.py -v
```

**Expected:** FAIL with "ModuleNotFoundError: No module named 'app.services.cdn_detector'"

**Step 3: 实现CDN识别服务**

```python
# app/services/cdn_detector.py
"""CDN检测与关联服务 - 识别CDN域名并关联原始域名"""
import re
from typing import Optional, Dict, Any, List

# CDN域名模式映射
CDN_PATTERN_MAP = {
    "cloudflare": [
        r"\.cdn\.cloudflare\.net$",
        r"\.cloudflare\.net$",
        r"\.cloudflare-dns\.com$",
    ],
    "aliyun": [
        r"\.w\.kunlunar\.com$",
        r"\.w\.alikunlun\.net$",
        r"\.aliyuncs\.com$",
    ],
    "tencent": [
        r"\.tc\.cdn$",
        r"\.cdn\.dnsv1\.com$",
    ],
    "baidu": [
        r"\.jomodns\.com$",
        r"\.bdydns\.net$",
    ],
    "huawei": [
        r"\.hc\.cdn$",
        r"\.cdnhwc([0-9]+)\.com$",
    ],
    "wangsu": [
        r"\.wscdns\.com$",
        r"\.cdn20\.com$",
    ],
    "qiniu": [
        r"\.qiniudns\.com$",
        r"\.clouddn\.com$",
    ],
    "aws": [
        r"\.cloudfront\.net$",
    ],
}


class CDNDetectorService:
    """CDN检测服务"""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.compiled_patterns = {}
        for provider, patterns in CDN_PATTERN_MAP.items():
            self.compiled_patterns[provider] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def detect_cdn(self, domain: str) -> Optional[str]:
        """
        检测域名是否属于CDN

        Args:
            domain: 域名

        Returns:
            CDN提供商名称 或 None
        """
        if not domain:
            return None

        domain_lower = domain.lower()

        for provider, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(domain_lower):
                    return provider

        return None

    def extract_original_domain(self, cdn_domain: str) -> str:
        """
        从CDN域名中提取原始域名

        Args:
            cdn_domain: CDN域名

        Returns:
            原始域名
        """
        cdn_provider = self.detect_cdn(cdn_domain)
        if not cdn_provider:
            return cdn_domain

        domain_lower = cdn_domain.lower()

        # Cloudflare: api.example.com.cdn.cloudflare.net -> api.example.com
        if cdn_provider == "cloudflare":
            if ".cdn.cloudflare.net" in domain_lower:
                return cdn_domain.replace(".cdn.cloudflare.net", "")
            if ".cloudflare.net" in domain_lower:
                return cdn_domain.replace(".cloudflare.net", "")

        # Aliyun: static.example.com.w.kunlunar.com -> static.example.com
        elif cdn_provider == "aliyun":
            if ".w.kunlunar.com" in domain_lower:
                return cdn_domain.replace(".w.kunlunar.com", "")
            if ".w.alikunlun.net" in domain_lower:
                return cdn_domain.replace(".w.alikunlun.net", "")
            if ".aliyuncs.com" in domain_lower:
                # 处理类似 bucket.oss-cn-hangzhou.aliyuncs.com
                return cdn_domain

        # Tencent: domain.tc.cdn -> domain
        elif cdn_provider == "tencent":
            if ".tc.cdn" in domain_lower:
                return cdn_domain.replace(".tc.cdn", "")

        # 默认返回原域名
        return cdn_domain

    def normalize_cdn_domain(self, domain: str) -> Dict[str, Any]:
        """
        标准化CDN域名信息

        Args:
            domain: 域名

        Returns:
            包含CDN信息的字典
        """
        cdn_provider = self.detect_cdn(domain)

        return {
            "cdn_domain": domain,
            "is_cdn": cdn_provider is not None,
            "cdn_provider": cdn_provider,
            "original_domain": self.extract_original_domain(domain) if cdn_provider else domain,
        }

    def batch_process(self, domains: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理域名列表

        Args:
            domains: 域名列表

        Returns:
            CDN信息列表
        """
        return [self.normalize_cdn_domain(domain) for domain in domains]

    def build_cdn_mapping(self, domains: List[str]) -> Dict[str, List[str]]:
        """
        构建原始域名到CDN域名的映射

        Args:
            domains: 域名列表

        Returns:
            {原始域名: [CDN域名列表]}
        """
        mapping = {}

        for domain in domains:
            info = self.normalize_cdn_domain(domain)
            if info["is_cdn"]:
                original = info["original_domain"]
                if original not in mapping:
                    mapping[original] = []
                mapping[original].append(domain)

        return mapping
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/services/test_cdn_detector.py -v
```

**Expected:** All tests PASS

**Step 5: 修改数据库模型添加CDN关联字段**

```python
# 修改 app/db/models.py 中 Asset 类
# 在第 191 行附近 (data = Column(JSON, default=dict) 之后) 添加：

    # CDN相关信息
    is_cdn = Column(Boolean, default=False, index=True)
    cdn_provider = Column(String(50), nullable=True, index=True)
    original_domain = Column(String(255), nullable=True, index=True)
```

**Step 6: 创建数据库迁移**

```bash
alembic revision -m "add cdn fields to assets"
```

**Step 7: 编辑迁移文件**

```python
# alembic/versions/xxxx_add_cdn_fields_to_assets.py
"""add cdn fields to assets

Revision ID: xxxx
Revises: yyyy
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxxx'
down_revision = 'yyyy'


def upgrade():
    op.add_column('assets', sa.Column('is_cdn', sa.Boolean(), nullable=True))
    op.add_column('assets', sa.Column('cdn_provider', sa.String(length=50), nullable=True))
    op.add_column('assets', sa.Column('original_domain', sa.String(length=255), nullable=True))

    # 创建索引
    op.create_index('ix_assets_is_cdn', 'assets', ['is_cdn'])
    op.create_index('ix_assets_cdn_provider', 'assets', ['cdn_provider'])
    op.create_index('ix_assets_original_domain', 'assets', ['original_domain'])

    # 设置默认值
    op.execute("UPDATE assets SET is_cdn = FALSE WHERE is_cdn IS NULL")


def downgrade():
    op.drop_index('ix_assets_original_domain', table_name='assets')
    op.drop_index('ix_assets_cdn_provider', table_name='assets')
    op.drop_index('ix_assets_is_cdn', table_name='assets')
    op.drop_column('assets', 'original_domain')
    op.drop_column('assets', 'cdn_provider')
    op.drop_column('assets', 'is_cdn')
```

**Step 8: 执行迁移**

```bash
alembic upgrade head
```

**Step 9: Commit**

```bash
git add tests/services/test_cdn_detector.py app/services/cdn_detector.py app/db/models.py alembic/versions/
git commit -m "feat: add CDN detection service and database fields for CDN domain association"
```

---

## Task 3: 增强资产去重聚合服务

**背景:** 24个域名存在重复记录，需要基于 (domain, ip, port) 三元组去重

**Files:**
- Create: `app/services/asset_dedup.py`
- Create: `tests/services/test_asset_dedup.py`
- Modify: `app/services/domain_aggregation.py`

### Step 1: 编写去重聚合服务的测试

```python
# tests/services/test_asset_dedup.py
import pytest
from datetime import datetime
from app.services.asset_dedup import AssetDedupService, generate_asset_key


def test_generate_asset_key():
    """测试资产键生成"""
    asset = {"domain": "api.example.com", "ip_address": "1.2.3.4", "port": 443}
    assert generate_asset_key(asset) == "api.example.com|1.2.3.4|443"

    # 测试空值处理
    asset = {"domain": None, "ip_address": "1.2.3.4", "port": 80}
    assert generate_asset_key(asset) == "|1.2.3.4|80"

    asset = {"domain": "example.com", "ip_address": None, "port": 443}
    assert generate_asset_key(asset) == "example.com||443"


def test_merge_asset_sources():
    """测试合并资产来源"""
    service = AssetDedupService()

    existing = {
        "sources": ["fofa"],
        "discovered_by": {"fofa": {"first_seen": "2026-03-01", "count": 1}},
        "data": {"fofa": {"raw": "data1"}},
    }

    new = {
        "sources": ["hunter"],
        "discovered_by": {"hunter": {"first_seen": "2026-03-02", "count": 1}},
        "data": {"hunter": {"raw": "data2"}},
    }

    result = service._merge_assets(existing, new)

    assert set(result["sources"]) == {"fofa", "hunter"}
    assert "fofa" in result["discovered_by"]
    assert "hunter" in result["discovered_by"]
    assert "fofa" in result["data"]
    assert "hunter" in result["data"]


def test_dedup_assets_by_key():
    """测试基于键的去重"""
    service = AssetDedupService()

    assets = [
        {"domain": "api.example.com", "ip_address": "1.2.3.4", "port": 443, "sources": ["fofa"]},
        {"domain": "api.example.com", "ip_address": "1.2.3.4", "port": 443, "sources": ["hunter"]},
        {"domain": "www.example.com", "ip_address": "1.2.3.5", "port": 80, "sources": ["fofa"]},
    ]

    result = service.dedup_assets(assets)

    # 应该合并为2条
    assert len(result) == 2

    # 检查第一条的source是否合并
    api_asset = [r for r in result if r["domain"] == "api.example.com"][0]
    assert set(api_asset["sources"]) == {"fofa", "hunter"}


def test_select_primary_asset():
    """测试主资产选择"""
    service = AssetDedupService()

    # 有更多字段的资产应被选为主资产
    asset1 = {"domain": "example.com", "product": None, "banner": None}
    asset2 = {"domain": "example.com", "product": "nginx", "banner": "Welcome"}

    primary = service._select_primary([asset1, asset2])
    assert primary["product"] == "nginx"


def test_calculate_duplicate_rate():
    """测试重复率计算"""
    service = AssetDedupService()

    assets = [
        {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80},
        {"domain": "a.com", "ip_address": "1.1.1.1", "port": 80},  # 重复
        {"domain": "b.com", "ip_address": "2.2.2.2", "port": 443},
    ]

    rate = service.calculate_duplicate_rate(assets)
    assert rate == 1/3  # 3条中有1条是重复的
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest tests/services/test_asset_dedup.py -v
```

**Step 3: 实现去重聚合服务**

```python
# app/services/asset_dedup.py
"""资产去重聚合服务 - 基于(domain, ip, port)三元组去重"""
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict


def generate_asset_key(asset: Dict[str, Any]) -> str:
    """
    生成资产唯一键

    Args:
        asset: 资产字典

    Returns:
        唯一键字符串
    """
    domain = asset.get("domain") or ""
    ip = asset.get("ip_address") or ""
    port = asset.get("port") or 0
    return f"{domain}|{ip}|{port}"


class AssetDedupService:
    """资产去重服务"""

    def dedup_assets(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于(domain, ip, port)去重并合并来源

        Args:
            assets: 资产列表

        Returns:
            去重后的资产列表
        """
        groups = defaultdict(list)

        # 按键分组
        for asset in assets:
            key = generate_asset_key(asset)
            groups[key].append(asset)

        # 合并每组
        result = []
        for key, group in groups.items():
            if len(group) == 1:
                result.append(group[0])
            else:
                merged = self._merge_group(group)
                result.append(merged)

        return result

    def _merge_group(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并同一组的多个资产

        Args:
            assets: 同一组的资产列表

        Returns:
            合并后的资产
        """
        # 选择最完整的作为主资产
        primary = self._select_primary(assets)

        # 合并其他资产的来源信息
        for other in assets:
            if other is not primary:
                primary = self._merge_assets(primary, other)

        # 标记为聚合资产
        primary["is_aggregated"] = True
        primary["aggregated_count"] = len(assets)

        return primary

    def _select_primary(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        选择最完整的资产作为主资产

        Args:
            assets: 资产列表

        Returns:
            主资产
        """
        def completeness_score(asset):
            score = 0
            if asset.get("product"):
                score += 3
            if asset.get("banner"):
                score += 2
            if asset.get("protocol"):
                score += 1
            if asset.get("data"):
                score += 1
            return score

        return max(assets, key=completeness_score)

    def _merge_assets(self, primary: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并两个资产的来源信息

        Args:
            primary: 主资产
            other: 其他资产

        Returns:
            合并后的资产
        """
        result = primary.copy()

        # 合并来源列表
        primary_sources = set(result.get("sources", []))
        other_sources = set(other.get("sources", []))
        result["sources"] = list(primary_sources | other_sources)

        # 合并 discovered_by
        primary_discovered = result.get("discovered_by", {})
        other_discovered = other.get("discovered_by", {})
        merged_discovered = primary_discovered.copy()
        for source, info in other_discovered.items():
            if source in merged_discovered:
                # 累加计数
                merged_discovered[source]["count"] = (
                    merged_discovered[source].get("count", 0) +
                    info.get("count", 0)
                )
            else:
                merged_discovered[source] = info
        result["discovered_by"] = merged_discovered

        # 合并 data
        primary_data = result.get("data", {})
        other_data = other.get("data", {})
        merged_data = primary_data.copy()
        for source, data in other_data.items():
            if source not in merged_data:
                merged_data[source] = data
        result["data"] = merged_data

        # 补充缺失字段
        for field in ["product", "banner", "protocol", "os"]:
            if not result.get(field) and other.get(field):
                result[field] = other[field]

        return result

    def calculate_duplicate_rate(self, assets: List[Dict[str, Any]]) -> float:
        """
        计算资产重复率

        Args:
            assets: 资产列表

        Returns:
            重复率 (0-1)
        """
        if not assets:
            return 0.0

        keys = [generate_asset_key(a) for a in assets]
        unique_keys = set(keys)

        return (len(keys) - len(unique_keys)) / len(keys)

    def find_duplicates(self, assets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        查找重复资产

        Args:
            assets: 资产列表

        Returns:
            {资产键: [重复资产列表]}
        """
        groups = defaultdict(list)
        for asset in assets:
            key = generate_asset_key(asset)
            groups[key].append(asset)

        # 只返回有重复的组
        return {k: v for k, v in groups.items() if len(v) > 1}
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/services/test_asset_dedup.py -v
```

**Step 5: Commit**

```bash
git add tests/services/test_asset_dedup.py app/services/asset_dedup.py
git commit -m "feat: add asset deduplication service based on domain+ip+port triplet"
```

---

## Task 4: 创建指纹增强服务

**背景:** 63.8%的资产缺少指纹信息，需要从现有数据中提取和增强

**Files:**
- Create: `app/services/fingerprint_enhancer.py`
- Create: `tests/services/test_fingerprint_enhancer.py`

### Step 1: 编写指纹增强服务的测试

```python
# tests/services/test_fingerprint_enhancer.py
import pytest
from app.services.fingerprint_enhancer import FingerprintEnhancerService


def test_extract_from_banner():
    """测试从banner提取指纹"""
    service = FingerprintEnhancerService()

    banner = "Server: nginx/1.18.0\nX-Powered-By: PHP/7.4.3"
    result = service.extract_from_banner(banner)

    assert "nginx" in result
    assert "PHP" in result


def test_extract_from_headers():
    """测试从headers提取指纹"""
    service = FingerprintEnhancerService()

    headers = {
        "Server": "Apache/2.4.41",
        "X-Powered-By": "Express",
        "X-Frame-Options": "SAMEORIGIN",
    }
    result = service.extract_from_headers(headers)

    assert "Apache" in result
    assert "Express" in result


def test_extract_from_title():
    """测试从页面title提取指纹"""
    service = FingerprintEnhancerService()

    title = "WordPress › Installation"
    result = service.extract_from_title(title)

    assert "WordPress" in result


def test_extract_from_url_path():
    """测试从URL路径提取指纹"""
    service = FingerprintEnhancerService()

    url = "http://example.com/wp-admin/install.php"
    result = service.extract_from_url_path(url)

    assert "WordPress" in result


def test_enhance_asset_with_fingerprint():
    """测试增强资产指纹信息"""
    service = FingerprintEnhancerService()

    asset = {
        "url": "http://example.com/wp-login.php",
        "banner": "Server: Apache/2.4\nX-Powered-By: PHP/7.4",
        "data": {
            "title": "WordPress Login",
            "headers": {"Server": "Apache"},
        },
        "product": None,
    }

    result = service.enhance_asset(asset)

    assert result["product"] is not None
    assert "Apache" in result.get("technologies", [])


def test_merge_with_existing_fingerprint():
    """测试与现有指纹合并"""
    service = FingerprintEnhancerService()

    asset = {
        "product": "nginx",
        "technologies": ["nginx"],
        "banner": "Server: nginx/1.18.0 (Ubuntu)",
    }

    result = service.enhance_asset(asset)

    assert "nginx" in result["technologies"]
    assert "Ubuntu" in result.get("technologies", [])
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest tests/services/test_fingerprint_enhancer.py -v
```

**Step 3: 实现指纹增强服务**

```python
# app/services/fingerprint_enhancer.py
"""指纹增强服务 - 从现有数据中提取和增强指纹信息"""
import re
from typing import Dict, Any, List, Optional, Set

# 指纹特征库
FINGERPRINT_PATTERNS = {
    # Web服务器
    "nginx": [r"nginx[\s/]", r"nginx-"],
    "Apache": [r"Apache[\s/]", r"apache.org"],
    "IIS": [r"Microsoft-IIS", r"IIS/"],
    "Tomcat": [r"Apache-Coyote", r"Tomcat"],
    "OpenResty": [r"openresty", r"OpenResty"],
    "Tengine": [r"Tengine[\s/]"],
    "Caddy": [r"Caddy"],

    # 编程语言/框架
    "PHP": [r"PHP[\s/]", r"X-Powered-By.*PHP"],
    "Express": [r"Express[\s/]"],
    "Django": [r"django", r"wsgiserver"],
    "Flask": [r"Werkzeug", r"flask"],
    "ASP.NET": [r"ASP.NET", r"X-AspNet-Version"],
    "Laravel": [r"laravel", r"laravel_session"],

    # CMS
    "WordPress": [r"wordpress", r"wp-content", r"wp-login", r"wp-admin"],
    "Drupal": [r"drupal", r"Drupal"],
    "Joomla": [r"joomla", r"Joomla"],

    # CDN/云服务
    "Cloudflare": [r"cloudflare", r"__cfduid", r"cf-ray"],

    # 操作系统
    "Ubuntu": [r"Ubuntu"],
    "CentOS": [r"CentOS"],
    "Debian": [r"Debian"],
    "Windows": [r"Win32", r"Windows"],
}


class FingerprintEnhancerService:
    """指纹增强服务"""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """编译指纹模式"""
        self.compiled_patterns = {}
        for tech, patterns in FINGERPRINT_PATTERNS.items():
            self.compiled_patterns[tech] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def extract_from_banner(self, banner: Optional[str]) -> Set[str]:
        """
        从服务banner提取指纹

        Args:
            banner: 服务banner

        Returns:
            检测到的技术集合
        """
        if not banner:
            return set()

        found = set()
        for tech, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(banner):
                    found.add(tech)
                    break
        return found

    def extract_from_headers(self, headers: Optional[Dict[str, Any]]) -> Set[str]:
        """
        从HTTP headers提取指纹

        Args:
            headers: HTTP头字典

        Returns:
            检测到的技术集合
        """
        if not headers:
            return set()

        found = set()
        header_text = "\n".join(f"{k}: {v}" for k, v in headers.items())

        for tech, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(header_text):
                    found.add(tech)
                    break
        return found

    def extract_from_title(self, title: Optional[str]) -> Set[str]:
        """
        从页面title提取指纹

        Args:
            title: 页面标题

        Returns:
            检测到的技术集合
        """
        if not title:
            return set()

        found = set()
        for tech, patterns in self.compINGERPRINT_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(title):
                    found.add(tech)
                    break
        return found

    def extract_from_url_path(self, url: Optional[str]) -> Set[str]:
        """
        从URL路径提取指纹

        Args:
            url: URL

        Returns:
            检测到的技术集合
        """
        if not url:
            return set()

        found = set()
        for tech, patterns in FINGERPRINT_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(url):
                    found.add(tech)
                    break
        return found

    def enhance_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强资产指纹信息

        Args:
            asset: 资产字典

        Returns:
            增强后的资产字典
        """
        result = asset.copy()
        all_techs = set()

        # 从各个来源提取
        banner = asset.get("banner")
        if banner:
            all_techs |= self.extract_from_banner(banner)

        data = asset.get("data", {})
        if isinstance(data, dict):
            headers = data.get("headers") or data.get("header")
            if headers:
                all_techs |= self.extract_from_headers(headers)

            title = data.get("title")
            if title:
                all_techs |= self.extract_from_title(title)

        url = asset.get("url")
        if url:
            all_techs |= self.extract_from_url_path(url)

        # 更新资产
        if all_techs:
            # 设置主要product（优先级）
            priority = ["nginx", "Apache", "IIS", "Tomcat", "OpenResty"]
            current_product = asset.get("product")

            if not current_product:
                for p in priority:
                    if p in all_techs:
                        result["product"] = p
                        break
                else:
                    # 取第一个检测到的
                    result["product"] = next(iter(all_techs))

            # 合并到technologies列表
            existing_techs = set(asset.get("technologies", []))
            result["technologies"] = list(existing_techs | all_techs)

        return result

    def batch_enhance(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量增强资产指纹

        Args:
            assets: 资产列表

        Returns:
            增强后的资产列表
        """
        return [self.enhance_asset(asset) for asset in assets]

    def calculate_fingerprint_coverage(self, assets: List[Dict[str, Any]]) -> float:
        """
        计算指纹覆盖率

        Args:
            assets: 资产列表

        Returns:
            覆盖率 (0-1)
        """
        if not assets:
            return 0.0

        has_fingerprint = sum(
            1 for a in assets
            if a.get("product") or a.get("technologies")
        )

        return has_fingerprint / len(assets)
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/services/test_fingerprint_enhancer.py -v
```

**Step 5: Commit**

```bash
git add tests/services/test_fingerprint_enhancer.py app/services/fingerprint_enhancer.py
git commit -m "feat: add fingerprint enhancement service to extract tech from banner/headers/title"
```

---

## Task 5: 创建资产处理流水线 (Pipeline)

**背景:** 整合所有服务，创建统一的资产处理流程

**Files:**
- Create: `app/services/asset_pipeline.py`
- Create: `tests/services/test_asset_pipeline.py`

### Step 1: 编写资产处理流水线的测试

```python
# tests/services/test_asset_pipeline.py
import pytest
from app.services.asset_pipeline import AssetPipeline


def test_pipeline_process_single_asset():
    """测试处理单个资产"""
    pipeline = AssetPipeline()

    asset = {
        "domain": "api.example.com",
        "ip_address": "1.2.3.4",
        "port": 443,
        "protocol": None,
        "banner": "Server: nginx/1.18.0",
        "product": None,
    }

    result = pipeline.process_asset(asset)

    # 应该推断出https协议
    assert result["protocol"] == "https"
    # 应该提取出nginx指纹
    assert result["product"] == "nginx"


def test_pipeline_batch_process():
    """测试批量处理"""
    pipeline = AssetPipeline()

    assets = [
        {
            "domain": "api.example.com",
            "ip_address": "1.2.3.4",
            "port": 80,
            "protocol": None,
            "sources": ["fofa"],
        },
        {
            "domain": "api.example.com",
            "ip_address": "1.2.3.4",
            "port": 80,
            "protocol": None,
            "sources": ["hunter"],
        },
        {
            "domain": "static.example.com.cdn.cloudflare.net",
            "ip_address": "2.3.4.5",
            "port": 443,
            "protocol": None,
        },
    ]

    results = pipeline.process_batch(assets)

    # 应该去重为2条
    assert len(results) == 2

    # 检查CDN处理
    cdn_asset = [r for r in results if "cloudflare" in r.get("cdn_domain", "")]
    if cdn_asset:
        assert cdn_asset[0]["is_cdn"] is True


def test_pipeline_stats():
    """测试流水线统计"""
    pipeline = AssetPipeline()

    assets = [
        {"protocol": None, "port": 80},
        {"protocol": "https", "port": 443},
        {"protocol": None, "port": 8080},
    ]

    results = pipeline.process_batch(assets)
    stats = pipeline.get_last_stats()

    assert stats["input_count"] == 3
    assert stats["output_count"] == 3
    assert stats["protocol_enhanced"] == 2
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest tests/services/test_asset_pipeline.py -v
```

**Step 3: 实现资产处理流水线**

```python
# app/services/asset_pipeline.py
"""资产处理流水线 - 整合CDN检测、协议推断、指纹增强和去重"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.services.cdn_detector import CDNDetectorService
from app.services.protocol_inference import ProtocolInferenceService
from app.services.fingerprint_enhancer import FingerprintEnhancerService
from app.services.asset_dedup import AssetDedupService


@dataclass
class PipelineStats:
    """流水线统计信息"""
    input_count: int = 0
    output_count: int = 0
    cdn_detected: int = 0
    protocol_enhanced: int = 0
    fingerprint_enhanced: int = 0
    dedup_removed: int = 0
    errors: List[str] = field(default_factory=list)


class AssetPipeline:
    """资产处理流水线"""

    def __init__(self):
        self.cdn_service = CDNDetectorService()
        self.protocol_service = ProtocolInferenceService()
        self.fingerprint_service = FingerprintEnhancerService()
        self.dedup_service = AssetDedupService()
        self.last_stats = PipelineStats()

    def process_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个资产

        处理流程:
        1. CDN检测与关联
        2. 协议推断
        3. 指纹增强

        Args:
            asset: 原始资产数据

        Returns:
            处理后的资产
        """
        result = asset.copy()

        try:
            # Step 1: CDN检测
            domain = result.get("domain")
            if domain:
                cdn_info = self.cdn_service.normalize_cdn_domain(domain)
                result.update({
                    "is_cdn": cdn_info["is_cdn"],
                    "cdn_provider": cdn_info["cdn_provider"],
                    "original_domain": cdn_info["original_domain"],
                })

            # Step 2: 协议推断
            if not result.get("protocol"):
                result = self.protocol_service.enhance_asset(result)

            # Step 3: 指纹增强
            result = self.fingerprint_service.enhance_asset(result)

        except Exception as e:
            self.last_stats.errors.append(f"Error processing asset: {e}")

        return result

    def process_batch(
        self,
        assets: List[Dict[str, Any]],
        enable_dedup: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        批量处理资产

        Args:
            assets: 资产列表
            enable_dedup: 是否启用去重

        Returns:
            处理后的资产列表
        """
        self.last_stats = PipelineStats()
        self.last_stats.input_count = len(assets)

        # Step 1: 逐个处理
        processed = []
        for asset in assets:
            processed.append(self.process_asset(asset))

        # Step 2: 去重
        if enable_dedup:
            deduped = self.dedup_service.dedup_assets(processed)
            self.last_stats.dedup_removed = len(processed) - len(deduped)
            processed = deduped

        self.last_stats.output_count = len(processed)
        self._calculate_stats(assets, processed)

        return processed

    def _calculate_stats(
        self,
        original: List[Dict[str, Any]],
        processed: List[Dict[str, Any]],
    ):
        """计算统计信息"""
        # CDN检测数
        self.last_stats.cdn_detected = sum(
            1 for a in processed if a.get("is_cdn")
        )

        # 协议增强数
        enhanced_protocol = 0
        for orig in original:
            if not orig.get("protocol"):
                enhanced_protocol += 1
        self.last_stats.protocol_enhanced = enhanced_protocol

        # 指纹增强数
        enhanced_fp = 0
        for orig in original:
            if not orig.get("product") and not orig.get("technologies"):
                enhanced_fp += 1
        self.last_stats.fingerprint_enhanced = enhanced_fp

    def get_last_stats(self) -> Dict[str, Any]:
        """获取上次处理的统计信息"""
        return {
            "input_count": self.last_stats.input_count,
            "output_count": self.last_stats.output_count,
            "cdn_detected": self.last_stats.cdn_detected,
            "protocol_enhanced": self.last_stats.protocol_enhanced,
            "fingerprint_enhanced": self.last_stats.fingerprint_enhanced,
            "dedup_removed": self.last_stats.dedup_removed,
            "error_count": len(self.last_stats.errors),
        }

    def get_improvement_report(self) -> Dict[str, Any]:
        """获取改进报告"""
        stats = self.get_last_stats()

        return {
            "summary": f"Processed {stats['input_count']} assets, "
                      f"output {stats['output_count']} unique assets",
            "improvements": {
                "protocol_coverage": f"+{stats['protocol_enhanced']} assets with inferred protocol",
                "fingerprint_coverage": f"+{stats['fingerprint_enhanced']} assets with enhanced fingerprint",
                "cdn_identification": f"{stats['cdn_detected']} CDN domains identified",
                "duplicates_removed": f"{stats['dedup_removed']} duplicate entries removed",
            },
            "errors": self.last_stats.errors[:10],  # 只显示前10个错误
        }
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/services/test_asset_pipeline.py -v
```

**Step 5: Commit**

```bash
git add tests/services/test_asset_pipeline.py app/services/asset_pipeline.py
git commit -m "feat: add asset processing pipeline to integrate all enhancement services"
```

---

## Task 6: 更新资产API端点

**背景:** 将新服务集成到现有API中

**Files:**
- Modify: `app/api/v1/endpoints/assets.py`
- Modify: `app/schemas/asset.py`

### Step 1: 修改Asset Schema添加新字段

```python
# app/schemas/asset.py - 添加新字段
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.db.models import AssetType


class AssetInDB(BaseModel):
    id: int
    type: AssetType
    value: str
    domain: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    product: Optional[str] = None
    url: Optional[str] = None
    data: Dict[str, Any]
    tags: List[str]
    sources: List[str] = []
    discovered_at: datetime
    last_seen: datetime
    tenant_id: int
    task_id: Optional[int]

    # 新增CDN相关字段
    is_cdn: bool = False
    cdn_provider: Optional[str] = None
    original_domain: Optional[str] = None

    # 新增聚合相关字段
    is_aggregated: bool = False
    aggregated_count: int = 1
    technologies: List[str] = []

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    items: List[AssetInDB]
    total: int


class AssetFilter(BaseModel):
    type: Optional[AssetType] = None
    task_id: Optional[int] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    # 新增过滤字段
    is_cdn: Optional[bool] = None
    cdn_provider: Optional[str] = None
    has_fingerprint: Optional[bool] = None


class AssetEnhanceRequest(BaseModel):
    """资产增强请求"""
    task_ids: Optional[List[int]] = None
    enable_cdn_detection: bool = True
    enable_protocol_inference: bool = True
    enable_fingerprint: bool = True
    enable_dedup: bool = True


class AssetEnhanceResponse(BaseModel):
    """资产增强响应"""
    processed: int
    enhanced: int
    report: Dict[str, Any]
```

**Step 2: 添加新的API端点**

```python
# 在 app/api/v1/endpoints/assets.py 末尾添加

from fastapi import BackgroundTasks
from app.services.asset_pipeline import AssetPipeline
from app.schemas.asset import AssetEnhanceRequest, AssetEnhanceResponse


@router.post("/enhance", response_model=AssetEnhanceResponse)
def enhance_assets(
    request: AssetEnhanceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    批量增强资产数据

    - CDN检测与关联
    - 协议推断
    - 指纹增强
    - 去重聚合
    """
    query = db.query(models.Asset).filter(models.Asset.tenant_id == tenant_id)

    if request.task_ids:
        query = query.filter(models.Asset.task_id.in_(request.task_ids))

    assets = query.all()

    # 转换为字典
    asset_dicts = []
    for a in assets:
        asset_dict = {
            "id": a.id,
            "domain": a.domain,
            "ip_address": a.ip_address,
            "port": a.port,
            "protocol": a.protocol,
            "product": a.product,
            "banner": a.data.get("banner") if a.data else None,
            "url": a.url,
            "data": a.data or {},
            "sources": a.sources or [],
        }
        asset_dicts.append(asset_dict)

    # 处理
    pipeline = AssetPipeline()
    results = pipeline.process_batch(
        asset_dicts,
        enable_dedup=request.enable_dedup,
    )

    # 更新数据库
    enhanced_count = 0
    for result in results:
        asset_id = result.get("id")
        if asset_id:
            asset = db.query(models.Asset).filter(
                models.Asset.id == asset_id,
                models.Asset.tenant_id == tenant_id,
            ).first()

            if asset:
                # 更新CDN信息
                if request.enable_cdn_detection:
                    asset.is_cdn = result.get("is_cdn", False)
                    asset.cdn_provider = result.get("cdn_provider")
                    asset.original_domain = result.get("original_domain")

                # 更新协议
                if request.enable_protocol_inference and result.get("protocol"):
                    asset.protocol = result["protocol"]

                # 更新指纹
                if request.enable_fingerprint:
                    if result.get("product"):
                        asset.product = result["product"]
                    if result.get("technologies"):
                        asset.data = asset.data or {}
                        asset.data["technologies"] = result["technologies"]

                enhanced_count += 1

    db.commit()

    return {
        "processed": len(assets),
        "enhanced": enhanced_count,
        "report": pipeline.get_improvement_report(),
    }


@router.get("/stats/quality")
def get_asset_quality_stats(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    获取资产数据质量统计
    """
    total = db.query(models.Asset).filter(
        models.Asset.tenant_id == tenant_id
    ).count()

    if total == 0:
        return {"total": 0, "message": "No assets found"}

    # 协议覆盖率
    with_protocol = db.query(models.Asset).filter(
        models.Asset.tenant_id == tenant_id,
        models.Asset.protocol.isnot(None),
    ).count()

    # 指纹覆盖率
    with_fingerprint = db.query(models.Asset).filter(
        models.Asset.tenant_id == tenant_id,
        models.Asset.product.isnot(None),
    ).count()

    # CDN资产数
    cdn_count = db.query(models.Asset).filter(
        models.Asset.tenant_id == tenant_id,
        models.Asset.is_cdn == True,
    ).count()

    # 多来源资产数
    multi_source = db.query(models.Asset).filter(
        models.Asset.tenant_id == tenant_id,
        models.Asset.sources.isnot(None),
    ).all()

    multi_source_count = sum(
        1 for a in multi_source
        if len(a.sources) > 1 if a.sources else False
    )

    return {
        "total": total,
        "coverage": {
            "protocol": {
                "count": with_protocol,
                "rate": round(with_protocol / total, 4),
            },
            "fingerprint": {
                "count": with_fingerprint,
                "rate": round(with_fingerprint / total, 4),
            },
        },
        "cdn": {
            "count": cdn_count,
            "rate": round(cdn_count / total, 4),
        },
        "multi_source": {
            "count": multi_source_count,
            "rate": round(multi_source_count / total, 4),
        },
    }
```

**Step 3: 运行测试**

```bash
python -m pytest tests/ -v -k "asset" --tb=short
```

**Step 4: Commit**

```bash
git add app/schemas/asset.py app/api/v1/endpoints/assets.py
git commit -m "feat: integrate enhancement services into asset API with /enhance and /stats/quality endpoints"
```

---

## Task 7: 创建前端资产质量仪表板

**背景:** 添加前端页面展示资产质量统计

**Files:**
- Create: `frontend/src/pages/AssetQuality.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx` (添加入口)

### Step 1: 创建资产质量仪表板组件

```tsx
// frontend/src/pages/AssetQuality.tsx
import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, Button, message, Table } from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloudServerOutlined,
  FingerprintOutlined,
} from '@ant-design/icons';

interface QualityStats {
  total: number;
  coverage: {
    protocol: { count: number; rate: number };
    fingerprint: { count: number; rate: number };
  };
  cdn: { count: number; rate: number };
  multi_source: { count: number; rate: number };
}

export const AssetQuality: React.FC = () => {
  const [stats, setStats] = useState<QualityStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [enhancing, setEnhancing] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/assets/stats/quality', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      message.error('Failed to fetch quality stats');
    } finally {
      setLoading(false);
    }
  };

  const handleEnhance = async () => {
    setEnhancing(true);
    try {
      const response = await fetch('/api/v1/assets/enhance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          enable_cdn_detection: true,
          enable_protocol_inference: true,
          enable_fingerprint: true,
          enable_dedup: true,
        }),
      });
      if (response.ok) {
        const result = await response.json();
        message.success(`Enhanced ${result.enhanced} assets`);
        fetchStats();
      }
    } catch (error) {
      message.error('Enhancement failed');
    } finally {
      setEnhancing(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const getProgressStatus = (rate: number) => {
    if (rate >= 0.9) return 'success';
    if (rate >= 0.7) return 'normal';
    return 'exception';
  };

  return (
    <div style={{ padding: '24px' }}>
      <h1>资产数据质量仪表板</h1>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总资产数"
              value={stats?.total || 0}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="协议覆盖率"
              value={Math.round((stats?.coverage.protocol.rate || 0) * 100)}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{
                color: (stats?.coverage.protocol.rate || 0) > 0.9 ? '#3f8600' : '#cf1322',
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="指纹覆盖率"
              value={Math.round((stats?.coverage.fingerprint.rate || 0) * 100)}
              suffix="%"
              prefix={<FingerprintOutlined />}
              valueStyle={{
                color: (stats?.coverage.fingerprint.rate || 0) > 0.7 ? '#3f8600' : '#cf1322',
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="CDN资产"
              value={stats?.cdn.count || 0}
              suffix={`(${Math.round((stats?.cdn.rate || 0) * 100)}%)`}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="覆盖率详情" loading={loading}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>
                协议识别: {stats?.coverage.protocol.count || 0} / {stats?.total || 0}
              </div>
              <Progress
                percent={Math.round((stats?.coverage.protocol.rate || 0) * 100)}
                status={getProgressStatus(stats?.coverage.protocol.rate || 0)}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>
                指纹识别: {stats?.coverage.fingerprint.count || 0} / {stats?.total || 0}
              </div>
              <Progress
                percent={Math.round((stats?.coverage.fingerprint.rate || 0) * 100)}
                status={getProgressStatus(stats?.coverage.fingerprint.rate || 0)}
              />
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="数据增强" loading={loading}>
            <p>点击以下按钮运行资产数据增强流程：</p>
            <ul>
              <li>自动识别CDN域名并关联原始域名</li>
              <li>基于端口推断HTTP/HTTPS协议</li>
              <li>从Banner/Headers提取指纹信息</li>
              <li>合并重复资产记录</li>
            </ul>
            <Button
              type="primary"
              onClick={handleEnhance}
              loading={enhancing}
              size="large"
              block
            >
              运行资产增强
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AssetQuality;
```

**Step 2: 添加路由**

在 `frontend/src/App.tsx` 或路由配置中添加：

```tsx
import { AssetQuality } from './pages/AssetQuality';

// 在路由中添加
<Route path="/asset-quality" element={<AssetQuality />} />
```

**Step 3: Commit**

```bash
git add frontend/src/pages/AssetQuality.tsx
git commit -m "feat: add asset quality dashboard with enhancement controls"
```

---

## Task 8: 集成测试与验证

**背景:** 验证所有服务集成后的效果

**Files:**
- Create: `tests/integration/test_asset_enhancement.py`

### Step 1: 编写集成测试

```python
# tests/integration/test_asset_enhancement.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.db import models

client = TestClient(app)


def test_asset_enhance_endpoint(auth_headers, db):
    """测试资产增强API端点"""
    # 创建测试资产
    tenant_id = 1

    # 创建测试数据
    test_assets = [
        {
            "domain": "test.example.com",
            "ip_address": "1.2.3.4",
            "port": 443,
            "protocol": None,
            "tenant_id": tenant_id,
        },
        {
            "domain": "test.example.com.cdn.cloudflare.net",
            "ip_address": "2.3.4.5",
            "port": 80,
            "protocol": None,
            "tenant_id": tenant_id,
        },
    ]

    for asset_data in test_assets:
        asset = models.Asset(**asset_data)
        db.add(asset)
    db.commit()

    # 调用增强API
    response = client.post(
        "/api/v1/assets/enhance",
        json={
            "enable_cdn_detection": True,
            "enable_protocol_inference": True,
            "enable_fingerprint": True,
            "enable_dedup": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["processed"] == 2
    assert result["enhanced"] > 0


def test_asset_quality_stats_endpoint(auth_headers):
    """测试资产质量统计API"""
    response = client.get(
        "/api/v1/assets/stats/quality",
        headers=auth_headers,
    )

    assert response.status_code == 200
    result = response.json()

    assert "total" in result
    assert "coverage" in result
    assert "protocol" in result["coverage"]
    assert "fingerprint" in result["coverage"]
    assert "cdn" in result


def test_end_to_end_pipeline():
    """测试完整流水线"""
    from app.services.asset_pipeline import AssetPipeline

    pipeline = AssetPipeline()

    # 模拟真实场景的数据
    raw_assets = [
        {
            "domain": "api.fofa.info",
            "ip_address": "104.20.18.45",
            "port": 443,
            "protocol": None,
            "banner": "Server: cloudflare\nCF-RAY: xxx",
            "sources": ["fofa"],
        },
        {
            "domain": "api.fofa.info",
            "ip_address": "104.20.18.45",
            "port": 443,
            "protocol": None,
            "banner": "Server: cloudflare",
            "sources": ["hunter"],
        },
        {
            "domain": "static.fofa.info.cdn.cloudflare.net",
            "ip_address": "172.66.161.110",
            "port": 80,
            "protocol": None,
            "sources": ["fofa"],
        },
    ]

    results = pipeline.process_batch(raw_assets)

    # 验证去重
    assert len(results) == 2  # 两条重复被合并

    # 验证CDN检测
    cdn_asset = [r for r in results if r.get("is_cdn")]
    assert len(cdn_asset) == 1
    assert cdn_asset[0]["cdn_provider"] == "cloudflare"
    assert cdn_asset[0]["original_domain"] == "static.fofa.info"

    # 验证协议推断
    for r in results:
        if r["port"] == 443:
            assert r["protocol"] == "https"
        elif r["port"] == 80:
            assert r["protocol"] == "http"

    # 验证来源合并
    api_asset = [r for r in results if r.get("domain") == "api.fofa.info"][0]
    assert set(api_asset["sources"]) == {"fofa", "hunter"}
    assert api_asset.get("is_aggregated") is True
```

**Step 2: 运行集成测试**

```bash
python -m pytest tests/integration/test_asset_enhancement.py -v
```

**Expected:** All tests PASS

**Step 3: Commit**

```bash
git add tests/integration/test_asset_enhancement.py
git commit -m "test: add integration tests for asset enhancement pipeline"
```

---

## 验收验证清单

运行以下命令验证所有功能：

```bash
# 1. 运行所有测试
python -m pytest tests/ -v --tb=short

# 2. 检查测试覆盖率
python -m pytest tests/ --cov=app.services --cov-report=term-missing

# 3. 验证服务可以启动
python -c "from app.services.asset_pipeline import AssetPipeline; p = AssetPipeline(); print('Pipeline OK')"

# 4. 使用真实数据验证（使用分析过的Excel数据）
python << 'EOF'
import pandas as pd
from app.services.asset_pipeline import AssetPipeline

# 加载测试数据
df = pd.read_excel('/Users/liqinggong/Downloads/资产列表_2026-03-08_15-00-07.xlsx')

# 转换为资产格式
assets = []
for _, row in df.iterrows():
    assets.append({
        "domain": row.get('域名') if row.get('域名') != '-' else None,
        "url": row.get('URL') if row.get('URL') != '-' else None,
        "ip_address": row.get('IP') if row.get('IP') != '-' else None,
        "port": int(row.get('端口')) if pd.notna(row.get('端口')) and row.get('端口') != '-' else None,
        "protocol": row.get('协议') if row.get('协议') != '-' else None,
        "product": row.get('指纹') if row.get('指纹') != '-' else None,
        "sources": row.get('来源', '').split('+') if pd.notna(row.get('来源')) else [],
    })

# 运行流水线
pipeline = AssetPipeline()
results = pipeline.process_batch(assets)

# 打印报告
print("="*60)
print("资产增强报告")
print("="*60)
import json
print(json.dumps(pipeline.get_improvement_report(), indent=2, ensure_ascii=False))

# 验证指标
stats = pipeline.get_last_stats()
print(f"\n原始资产数: {stats['input_count']}")
print(f"去重后资产数: {stats['output_count']}")
print(f"CDN识别数: {stats['cdn_detected']}")
print(f"协议增强数: {stats['protocol_enhanced']}")
print(f"指纹增强数: {stats['fingerprint_enhanced']}")
print(f"去重移除: {stats['dedup_removed']}")
EOF
```

---

## 总结

本计划实现以下改进：

| 功能 | 状态 | 文件 |
|------|------|------|
| 协议推断服务 | ✅ | `app/services/protocol_inference.py` |
| CDN检测与关联 | ✅ | `app/services/cdn_detector.py` |
| 资产去重聚合 | ✅ | `app/services/asset_dedup.py` |
| 指纹增强 | ✅ | `app/services/fingerprint_enhancer.py` |
| 统一流水线 | ✅ | `app/services/asset_pipeline.py` |
| API集成 | ✅ | `app/api/v1/endpoints/assets.py` |
| 前端仪表板 | ✅ | `frontend/src/pages/AssetQuality.tsx` |

**验收指标：**
- 协议覆盖率从 62.4% 提升至 >95%
- CDN识别率 >90%
- 指纹覆盖率从 36.2% 提升至 >70%
- 重复域名从24个降至 <5个
