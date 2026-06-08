"""
Residential Proxy Manager — Security Research Tool
Supports: HTTP, HTTPS, SOCKS5
Features: rotation, health check, geo-targeting, failover
"""

import asyncio
import random
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path

import httpx

logger = logging.getLogger("ProxyManager")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ProxyProtocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class Proxy:
    host: str
    port: int
    username: str = ""
    password: str = ""
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    country: str = ""
    city: str = ""

    # Runtime stats
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0.0
    last_checked: float = 0.0
    is_alive: bool = True
    response_time_ms: float = 0.0

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return (self.success_count / total * 100) if total > 0 else 0.0

    def to_httpx_dict(self) -> dict:
        return {"http://": self.url, "https://": self.url}

    def __repr__(self):
        return f"Proxy({self.host}:{self.port} [{self.country}] rate={self.success_rate:.0f}%)"


class RotationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"
    FASTEST = "fastest"
    BEST_SUCCESS = "best_success"


class ProxyManager:
    def __init__(
        self,
        rotation_strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        health_check_url: str = "https://httpbin.org/ip",
        health_check_interval: int = 300,
        max_fails: int = 3,
        request_timeout: int = 15,
    ):
        self.proxies: list[Proxy] = []
        self.strategy = rotation_strategy
        self.health_check_url = health_check_url
        self.health_check_interval = health_check_interval
        self.max_fails = max_fails
        self.request_timeout = request_timeout
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_from_list(self, proxy_list: list[str], protocol: ProxyProtocol = ProxyProtocol.HTTP):
        """
        Load proxies from a list of strings.
        Formats:
          host:port
          host:port:user:pass
          protocol://user:pass@host:port
        """
        for line in proxy_list:
            proxy = self._parse_proxy_string(line.strip(), protocol)
            if proxy:
                self.proxies.append(proxy)
        logger.info(f"Loaded {len(self.proxies)} proxies")

    def load_from_file(self, path: str, protocol: ProxyProtocol = ProxyProtocol.HTTP):
        lines = Path(path).read_text().splitlines()
        self.load_from_list([l for l in lines if l and not l.startswith("#")], protocol)

    def load_from_json(self, path: str):
        data = json.loads(Path(path).read_text())
        for item in data:
            proxy = Proxy(
                host=item["host"],
                port=item["port"],
                username=item.get("username", ""),
                password=item.get("password", ""),
                protocol=ProxyProtocol(item.get("protocol", "http")),
                country=item.get("country", ""),
                city=item.get("city", ""),
            )
            self.proxies.append(proxy)
        logger.info(f"Loaded {len(self.proxies)} proxies from JSON")

    def _parse_proxy_string(self, line: str, protocol: ProxyProtocol) -> Optional[Proxy]:
        try:
            # protocol://user:pass@host:port
            if "://" in line:
                from urllib.parse import urlparse
                p = urlparse(line)
                return Proxy(
                    host=p.hostname,
                    port=p.port,
                    username=p.username or "",
                    password=p.password or "",
                    protocol=ProxyProtocol(p.scheme),
                )
            parts = line.split(":")
            if len(parts) == 2:
                return Proxy(host=parts[0], port=int(parts[1]), protocol=protocol)
            if len(parts) == 4:
                return Proxy(host=parts[0], port=int(parts[1]), username=parts[2], password=parts[3], protocol=protocol)
        except Exception as e:
            logger.warning(f"Could not parse proxy '{line}': {e}")
        return None

    # ── Selection ─────────────────────────────────────────────────────────────

    def get_alive_proxies(self, country: str = "") -> list[Proxy]:
        proxies = [p for p in self.proxies if p.is_alive and p.fail_count < self.max_fails]
        if country:
            proxies = [p for p in proxies if p.country.lower() == country.lower()]
        return proxies

    def get_proxy(self, country: str = "") -> Optional[Proxy]:
        alive = self.get_alive_proxies(country)
        if not alive:
            logger.warning("No alive proxies available")
            return None

        if self.strategy == RotationStrategy.ROUND_ROBIN:
            proxy = alive[self._round_robin_index % len(alive)]
            self._round_robin_index += 1
        elif self.strategy == RotationStrategy.RANDOM:
            proxy = random.choice(alive)
        elif self.strategy == RotationStrategy.LEAST_USED:
            proxy = min(alive, key=lambda p: p.last_used)
        elif self.strategy == RotationStrategy.FASTEST:
            proxy = min(alive, key=lambda p: p.response_time_ms or float("inf"))
        elif self.strategy == RotationStrategy.BEST_SUCCESS:
            proxy = max(alive, key=lambda p: p.success_rate)
        else:
            proxy = random.choice(alive)

        proxy.last_used = time.time()
        return proxy

    # ── Health Check ──────────────────────────────────────────────────────────

    async def check_proxy(self, proxy: Proxy) -> bool:
        start = time.time()
        try:
            async with httpx.AsyncClient(
                proxies=proxy.to_httpx_dict(),
                timeout=self.request_timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(self.health_check_url)
                elapsed = (time.time() - start) * 1000
                proxy.response_time_ms = elapsed
                proxy.last_checked = time.time()

                if resp.status_code == 200:
                    proxy.is_alive = True
                    proxy.success_count += 1
                    ip_info = resp.json().get("origin", "unknown")
                    logger.debug(f"✅ {proxy.host}:{proxy.port} alive | IP: {ip_info} | {elapsed:.0f}ms")
                    return True
        except Exception as e:
            logger.debug(f"❌ {proxy.host}:{proxy.port} dead: {e}")

        proxy.is_alive = False
        proxy.fail_count += 1
        proxy.last_checked = time.time()
        return False

    async def check_all(self, concurrency: int = 10):
        logger.info(f"Checking {len(self.proxies)} proxies (concurrency={concurrency})")
        sem = asyncio.Semaphore(concurrency)

        async def _check(proxy):
            async with sem:
                await self.check_proxy(proxy)

        await asyncio.gather(*[_check(p) for p in self.proxies])
        alive = sum(1 for p in self.proxies if p.is_alive)
        logger.info(f"Health check done: {alive}/{len(self.proxies)} alive")

    async def start_health_monitor(self, concurrency: int = 10):
        """Background task — re-checks proxies every health_check_interval seconds."""
        while True:
            await self.check_all(concurrency)
            await asyncio.sleep(self.health_check_interval)

    # ── Request Helper ────────────────────────────────────────────────────────

    async def get(self, url: str, retries: int = 3, country: str = "", **kwargs) -> Optional[httpx.Response]:
        """Make a GET request through a rotating proxy with automatic retry."""
        for attempt in range(retries):
            proxy = self.get_proxy(country)
            if not proxy:
                return None
            try:
                async with httpx.AsyncClient(
                    proxies=proxy.to_httpx_dict(),
                    timeout=self.request_timeout,
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(url, **kwargs)
                    proxy.success_count += 1
                    return resp
            except Exception as e:
                proxy.fail_count += 1
                if proxy.fail_count >= self.max_fails:
                    proxy.is_alive = False
                logger.warning(f"Attempt {attempt+1}/{retries} failed via {proxy.host}: {e}")
                await asyncio.sleep(random.uniform(1, 3))
        return None

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        alive = self.get_alive_proxies()
        countries = {}
        for p in alive:
            c = p.country or "unknown"
            countries[c] = countries.get(c, 0) + 1
        avg_rt = sum(p.response_time_ms for p in alive if p.response_time_ms) / max(len(alive), 1)
        return {
            "total": len(self.proxies),
            "alive": len(alive),
            "dead": len(self.proxies) - len(alive),
            "avg_response_time_ms": round(avg_rt, 1),
            "countries": countries,
        }

    def print_stats(self):
        s = self.stats()
        print(f"\n{'='*40}")
        print(f"  Proxy Pool Stats")
        print(f"{'='*40}")
        print(f"  Total   : {s['total']}")
        print(f"  Alive   : {s['alive']}")
        print(f"  Dead    : {s['dead']}")
        print(f"  Avg RT  : {s['avg_response_time_ms']} ms")
        print(f"  Countries: {s['countries']}")
        print(f"{'='*40}\n")


# ── Convenience wrapper ───────────────────────────────────────────────────────

class ResidentialProxyPool(ProxyManager):
    """
    Pre-configured for residential proxy providers.
    Supports BrightData, IPRoyal, Oxylabs, SOAX sticky/rotating endpoints.
    """

    @classmethod
    def from_brightdata(cls, username: str, password: str, country: str = "us") -> "ResidentialProxyPool":
        pool = cls(rotation_strategy=RotationStrategy.ROUND_ROBIN)
        # BrightData rotating residential endpoint
        proxy = Proxy(
            host="brd.superproxy.io",
            port=22225,
            username=f"{username}-country-{country}",
            password=password,
            protocol=ProxyProtocol.HTTP,
            country=country,
        )
        pool.proxies.append(proxy)
        return pool

    @classmethod
    def from_iproyal(cls, username: str, password: str) -> "ResidentialProxyPool":
        pool = cls(rotation_strategy=RotationStrategy.RANDOM)
        proxy = Proxy(
            host="geo.iproyal.com",
            port=12321,
            username=username,
            password=password,
            protocol=ProxyProtocol.HTTP,
        )
        pool.proxies.append(proxy)
        return pool

    @classmethod
    def from_oxylabs(cls, username: str, password: str, country: str = "us") -> "ResidentialProxyPool":
        pool = cls(rotation_strategy=RotationStrategy.ROUND_ROBIN)
        proxy = Proxy(
            host="pr.oxylabs.io",
            port=7777,
            username=f"customer-{username}-cc-{country.upper()}",
            password=password,
            protocol=ProxyProtocol.HTTP,
            country=country,
        )
        pool.proxies.append(proxy)
        return pool


# ── CLI / Demo ────────────────────────────────────────────────────────────────

async def demo():
    manager = ProxyManager(
        rotation_strategy=RotationStrategy.FASTEST,
        health_check_url="https://httpbin.org/ip",
        request_timeout=10,
    )

    # Load sample proxies (replace with real ones)
    sample_proxies = [
        "1.2.3.4:8080",
        "http://user:pass@5.6.7.8:3128",
    ]
    manager.load_from_list(sample_proxies)

    # Health check all
    await manager.check_all(concurrency=5)
    manager.print_stats()

    # Make a request through best proxy
    resp = await manager.get("https://httpbin.org/ip")
    if resp:
        print(f"Response IP: {resp.json()}")


if __name__ == "__main__":
    asyncio.run(demo())
