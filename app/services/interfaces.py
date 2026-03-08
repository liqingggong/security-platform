from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class SearchRecord:
    ip: str
    port: int
    link: str
    product: Optional[str] = None
    raw: Optional[Any] = None


@dataclass(frozen=True)
class SubdomainRecord:
    root_domain: str
    subdomain: str
    source: str
    resolved_ips: Optional[List[str]] = None
    raw: Optional[Any] = None


@dataclass(frozen=True)
class ServiceRecord:
    ip: str
    port: int
    transport: str = "tcp"
    product: Optional[str] = None
    banner: Optional[str] = None
    detected_by: Optional[str] = None
    raw: Optional[Any] = None


@dataclass(frozen=True)
class FingerprintResult:
    target: str  # endpoint or ip:port
    product: Optional[str] = None
    version: Optional[str] = None
    tags: Optional[List[str]] = None
    confidence: float = 0.5
    evidence: Optional[Any] = None


@dataclass(frozen=True)
class VulnFinding:
    target: str
    vuln_id: Optional[str]
    severity: Optional[str]
    title: Optional[str] = None
    proof: Optional[Any] = None
    raw: Optional[Any] = None


class IAssetSearchProvider(Protocol):
    def search(self, query: str, fields: List[str], limit: int = 1000) -> List[SearchRecord]:
        ...


class ISubdomainEnumerator(Protocol):
    def enumerate(self, root_domains: List[str], options: Optional[Dict[str, Any]] = None) -> List[SubdomainRecord]:
        ...


class IPortDiscovery(Protocol):
    def discover(self, ips: List[str], options: Optional[Dict[str, Any]] = None) -> List[ServiceRecord]:
        ...


class IFingerprintEngine(Protocol):
    def fingerprint(self, targets: List[str], options: Optional[Dict[str, Any]] = None) -> List[FingerprintResult]:
        ...


class IVulnScanner(Protocol):
    def scan(
        self,
        targets: List[str],
        fingerprints: Optional[List[FingerprintResult]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[VulnFinding]:
        ...


@dataclass
class PipelineInput:
    root_domains: List[str]
    ips: List[str]
    enable: Dict[str, bool]
    options: Optional[Dict[str, Any]] = None


@dataclass
class PipelineOutput:
    search_records: List[SearchRecord]
    subdomains: List[SubdomainRecord]
    services: List[ServiceRecord]
    fingerprints: List[FingerprintResult]
    findings: List[VulnFinding]


class IPipeline(Protocol):
    def run(self, tenant_id: int, task_id: int, input: PipelineInput) -> PipelineOutput:
        ...
