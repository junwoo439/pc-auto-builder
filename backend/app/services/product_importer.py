import ipaddress
import json
import re
import socket
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from app.data.database import (
    connect_database,
    extract_source_url,
    initialize_database,
)


USER_AGENT = "PC-Auto-Builder/1.1"
REQUEST_DELAY_SECONDS = 1.0
TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5


def _validate_public_host(hostname: str, port: int) -> None:
    lowered = hostname.rstrip(".").casefold()
    if lowered in {"localhost", "localhost.localdomain"}:
        raise ValueError("로컬/내부 네트워크 주소는 수집할 수 없습니다.")

    try:
        addresses = socket.getaddrinfo(
            hostname.encode("idna").decode("ascii"),
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as error:
        raise ValueError("도메인 주소를 확인할 수 없습니다.") from error

    if not addresses:
        raise ValueError("도메인 주소를 확인할 수 없습니다.")

    for address in addresses:
        ip_text = address[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError as error:
            raise ValueError("서버 IP 주소를 확인할 수 없습니다.") from error

        if not ip.is_global:
            raise ValueError("로컬/사설/예약 IP 주소는 수집할 수 없습니다.")


def normalize_url(url: str) -> str:
    normalized = url.strip()
    parsed = urlparse(normalized)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("http:// 또는 https://로 시작해야 합니다.")
    if not parsed.hostname:
        raise ValueError("도메인 주소가 없습니다.")
    if parsed.username or parsed.password:
        raise ValueError("사용자 정보가 포함된 URL은 허용하지 않습니다.")

    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as error:
        raise ValueError("URL 포트가 올바르지 않습니다.") from error

    _validate_public_host(parsed.hostname, port)

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )


def _download_text(
    url: str,
    *,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, str, str]:
    session = requests.Session()
    session.trust_env = False
    current_url = normalize_url(url)
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        **(headers or {}),
    }

    try:
        for _ in range(MAX_REDIRECTS + 1):
            response = session.get(
                current_url,
                headers=request_headers,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )

            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise ValueError("리다이렉트 주소가 없습니다.")
                current_url = normalize_url(urljoin(current_url, location))
                continue

            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > MAX_RESPONSE_BYTES:
                        response.close()
                        raise ValueError("응답 크기가 2MB 제한을 초과했습니다.")
                except ValueError as error:
                    if "제한" in str(error):
                        raise

            body = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    response.close()
                    raise ValueError("응답 크기가 2MB 제한을 초과했습니다.")

            encoding = response.encoding or "utf-8"
            text = bytes(body).decode(encoding, errors="replace")
            content_type = response.headers.get("Content-Type", "")
            status_code = response.status_code
            response.close()
            return status_code, text, content_type, current_url

        raise ValueError("리다이렉트 횟수가 너무 많습니다.")
    except requests.RequestException as error:
        raise ValueError(f"웹 요청 실패: {error}") from error
    finally:
        session.close()


def robots_allows(url: str) -> tuple[bool, str]:
    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        status, text, _, final_url = _download_text(
            robots_url,
            timeout=8,
            headers={"Accept": "text/plain,*/*;q=0.1"},
        )
    except ValueError as error:
        return False, f"robots.txt를 확인하지 못했습니다: {error}"

    if status == 404:
        return True, ""
    if not 200 <= status < 300:
        return False, f"robots.txt 확인 실패: HTTP {status}"

    parser = RobotFileParser()
    parser.set_url(final_url)
    parser.parse(text.splitlines())

    if not parser.can_fetch(USER_AGENT, normalized_url):
        return False, "robots.txt에서 수집을 허용하지 않습니다."

    return True, ""


def fetch_html(url: str) -> str:
    normalized_url = normalize_url(url)
    allowed, reason = robots_allows(normalized_url)
    if not allowed:
        raise ValueError(reason)

    status, text, content_type, _ = _download_text(
        normalized_url,
        timeout=TIMEOUT_SECONDS,
        headers={"Accept": "text/html,application/xhtml+xml"},
    )

    if not 200 <= status < 300:
        raise ValueError(f"상품 페이지 요청 실패: HTTP {status}")
    if "text/html" not in content_type.lower():
        raise ValueError("HTML 페이지가 아닙니다.")

    return text


def iter_json_nodes(value: object):
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from iter_json_nodes(child)

    elif isinstance(value, list):
        for child in value:
            yield from iter_json_nodes(child)


def read_json_ld(
    soup: BeautifulSoup,
) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []

    scripts = soup.select(
        'script[type="application/ld+json"]'
    )

    for script in scripts:
        raw_text = script.string or script.get_text()

        if not raw_text.strip():
            continue

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            continue

        for node in iter_json_nodes(data):
            nodes.append(node)

    return nodes


def type_contains(
    node: dict[str, object],
    expected_type: str,
) -> bool:
    node_type = node.get("@type")

    if isinstance(node_type, str):
        return node_type.lower() == expected_type.lower()

    if isinstance(node_type, list):
        return any(
            str(value).lower() == expected_type.lower()
            for value in node_type
        )

    return False


def discover_product_urls(
    seed_url: str,
    limit: int,
) -> list[str]:
    html = fetch_html(seed_url)
    soup = BeautifulSoup(html, "html.parser")

    discovered: list[str] = []
    seed_domain = urlparse(seed_url).netloc

    nodes = read_json_ld(soup)

    if any(
        type_contains(node, "Product")
        for node in nodes
    ):
        discovered.append(seed_url)

    for node in nodes:
        if not type_contains(node, "ItemList"):
            continue

        elements = node.get("itemListElement", [])

        if not isinstance(elements, list):
            continue

        for element in elements:
            if not isinstance(element, dict):
                continue

            item = element.get("item", element)

            if isinstance(item, dict):
                candidate = (
                    item.get("url")
                    or item.get("@id")
                )
            else:
                candidate = item

            if not isinstance(candidate, str):
                continue

            absolute_url = urljoin(
                seed_url,
                candidate,
            )

            if urlparse(absolute_url).netloc != seed_domain:
                continue

            discovered.append(absolute_url)

    selectors = [
        '[itemtype*="Product"] a[href]',
        ".product a[href]",
        ".product-item a[href]",
        ".prdList a[href]",
        'a[href*="/product/"]',
        'a[href*="/products/"]',
        'a[href*="productDetail"]',
    ]

    for selector in selectors:
        for link in soup.select(selector):
            href = link.get("href")

            if not href:
                continue

            absolute_url = urljoin(seed_url, href)

            if urlparse(absolute_url).netloc != seed_domain:
                continue

            discovered.append(absolute_url)

    unique_urls: list[str] = []

    for url in discovered:
        clean_url = url.split("#")[0]

        if clean_url in unique_urls:
            continue

        unique_urls.append(clean_url)

        if len(unique_urls) >= limit:
            break

    if not unique_urls:
        unique_urls.append(seed_url)

    return unique_urls


def parse_number(value: object) -> int | None:
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return round(value)

    if not isinstance(value, str):
        return None

    cleaned = re.sub(
        r"[^0-9.]",
        "",
        value,
    )

    if not cleaned:
        return None

    try:
        return round(float(cleaned))
    except ValueError:
        return None


def extract_price(
    product: dict[str, object],
    soup: BeautifulSoup,
) -> tuple[int | None, str | None]:
    offers = product.get("offers")
    offer_items: list[dict[str, object]] = []

    if isinstance(offers, dict):
        offer_items.append(offers)

    elif isinstance(offers, list):
        offer_items.extend(
            offer
            for offer in offers
            if isinstance(offer, dict)
        )

    prices: list[int] = []
    currency: str | None = None

    for offer in offer_items:
        price_value = (
            offer.get("price")
            or offer.get("lowPrice")
            or offer.get("highPrice")
        )

        parsed_price = parse_number(price_value)

        if parsed_price is not None:
            prices.append(parsed_price)

        if currency is None:
            currency_value = offer.get("priceCurrency")

            if currency_value:
                currency = str(currency_value)

    if prices:
        return min(prices), currency

    meta_selectors = [
        'meta[property="product:price:amount"]',
        'meta[itemprop="price"]',
        '[itemprop="price"]',
    ]

    for selector in meta_selectors:
        element = soup.select_one(selector)

        if element is None:
            continue

        raw_price = (
            element.get("content")
            or element.get("value")
            or element.get_text()
        )

        parsed_price = parse_number(raw_price)

        if parsed_price is not None:
            return parsed_price, currency

    return None, currency


def extract_brand(
    product: dict[str, object],
) -> str:
    brand = product.get("brand")

    if isinstance(brand, dict):
        name = brand.get("name")

        if name:
            return str(name).strip()

    if isinstance(brand, str):
        return brand.strip()

    manufacturer = product.get("manufacturer")

    if isinstance(manufacturer, dict):
        name = manufacturer.get("name")

        if name:
            return str(name).strip()

    if isinstance(manufacturer, str):
        return manufacturer.strip()

    return "미확인"


def extract_product(
    url: str,
    category: str,
) -> dict[str, object]:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    nodes = read_json_ld(soup)

    product = next(
        (
            node
            for node in nodes
            if type_contains(node, "Product")
        ),
        {},
    )

    name = product.get("name")

    if not name:
        title_meta = soup.select_one(
            'meta[property="og:title"]'
        )

        if title_meta is not None:
            name = title_meta.get("content")

    if not name and soup.title is not None:
        name = soup.title.get_text(strip=True)

    if not name:
        raise ValueError("제품명을 찾지 못했습니다.")

    price, currency = extract_price(
        product,
        soup,
    )

    if price is None:
        raise ValueError("가격을 찾지 못했습니다.")

    manufacturer = extract_brand(product)

    specifications: dict[str, object] = {
        "source_url": url,
        "source_name": urlparse(url).netloc,
        "last_checked_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    if currency:
        specifications["currency"] = currency

    for key in ["sku", "mpn", "gtin", "model"]:
        value = product.get(key)

        if value:
            specifications[key] = str(value)

    source_category = product.get("category")

    if source_category:
        specifications["source_category"] = str(
            source_category
        )

    additional_properties = product.get(
        "additionalProperty",
        [],
    )

    if isinstance(additional_properties, dict):
        additional_properties = [
            additional_properties
        ]

    if isinstance(additional_properties, list):
        for prop in additional_properties:
            if not isinstance(prop, dict):
                continue

            prop_name = prop.get("name")
            prop_value = prop.get("value")

            if not prop_name or prop_value is None:
                continue

            specifications[str(prop_name)] = str(
                prop_value
            )

    return {
        "category": category,
        "manufacturer": manufacturer,
        "model_name": str(name).strip(),
        "price": price,
        "specifications": specifications,
    }


def _existing_product_row(
    connection: sqlite3.Connection,
    product: dict[str, object],
    source_url: str | None,
):
    if source_url:
        row = connection.execute(
            "SELECT * FROM parts WHERE source_url = ? LIMIT 1",
            (source_url,),
        ).fetchone()
        if row is not None:
            return row

    return connection.execute(
        """
        SELECT *
        FROM parts
        WHERE LOWER(category) = LOWER(?)
          AND LOWER(manufacturer) = LOWER(?)
          AND LOWER(model_name) = LOWER(?)
        LIMIT 1
        """,
        (
            product["category"],
            product["manufacturer"],
            product["model_name"],
        ),
    ).fetchone()


def upsert_product(
    product: dict[str, object],
) -> tuple[str, int]:
    initialize_database()
    specifications = product["specifications"]

    if not isinstance(specifications, dict):
        raise ValueError("제품 규격 형식이 잘못되었습니다.")

    source_url = extract_source_url(specifications)

    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = _existing_product_row(connection, product, source_url)
        old_specifications: dict[str, object] = {}

        if existing is not None:
            try:
                parsed = json.loads(existing["specifications"])
                if isinstance(parsed, dict):
                    old_specifications = parsed
            except json.JSONDecodeError:
                pass

        merged_specs = {**old_specifications, **specifications}
        serialized_specs = json.dumps(merged_specs, ensure_ascii=False)

        if existing is not None:
            existing_id = int(existing["id"])
            connection.execute(
                """
                UPDATE parts
                SET category = ?, manufacturer = ?, model_name = ?,
                    price = ?, specifications = ?, source_url = ?
                WHERE id = ?
                """,
                (
                    product["category"],
                    product["manufacturer"],
                    product["model_name"],
                    product["price"],
                    serialized_specs,
                    source_url,
                    existing_id,
                ),
            )
            connection.commit()
            return "updated", existing_id

        try:
            cursor = connection.execute(
                """
                INSERT INTO parts (
                    category, manufacturer, model_name, price,
                    specifications, source_url
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    product["category"],
                    product["manufacturer"],
                    product["model_name"],
                    product["price"],
                    serialized_specs,
                    source_url,
                ),
            )
            connection.commit()
            return "created", int(cursor.lastrowid)
        except sqlite3.IntegrityError:
            # 다른 수집 작업이 같은 상품을 먼저 저장한 경우 다시 조회해 갱신합니다.
            existing = _existing_product_row(connection, product, source_url)
            if existing is None:
                raise

            existing_id = int(existing["id"])
            connection.execute(
                """
                UPDATE parts
                SET category = ?, manufacturer = ?, model_name = ?,
                    price = ?, specifications = ?, source_url = ?
                WHERE id = ?
                """,
                (
                    product["category"],
                    product["manufacturer"],
                    product["model_name"],
                    product["price"],
                    serialized_specs,
                    source_url,
                    existing_id,
                ),
            )
            connection.commit()
            return "updated", existing_id


def import_from_urls(
    seed_urls: list[str],
    category: str,
    discover_links: bool,
    max_products: int,
) -> dict[str, object]:
    product_urls: list[str] = []
    discovery_errors: list[dict[str, str]] = []

    for seed_url in seed_urls:
        try:
            normalized_seed = normalize_url(seed_url)

            if discover_links:
                discovered = discover_product_urls(
                    normalized_seed,
                    max_products,
                )
            else:
                discovered = [normalized_seed]

            for url in discovered:
                if url not in product_urls:
                    product_urls.append(url)

                if len(product_urls) >= max_products:
                    break

        except Exception as error:
            discovery_errors.append(
                {
                    "url": seed_url,
                    "status": "failed",
                    "message": str(error),
                }
            )

        if len(product_urls) >= max_products:
            break

    results: list[dict[str, object]] = []
    created = 0
    updated = 0

    for index, product_url in enumerate(product_urls):
        try:
            product = extract_product(
                product_url,
                category,
            )

            action, part_id = upsert_product(product)

            if action == "created":
                created += 1
            else:
                updated += 1

            results.append(
                {
                    "url": product_url,
                    "status": action,
                    "part_id": part_id,
                    "model_name": product["model_name"],
                    "price": product["price"],
                    "message": (
                        "새 부품 추가"
                        if action == "created"
                        else "기존 부품 갱신"
                    ),
                }
            )

        except Exception as error:
            results.append(
                {
                    "url": product_url,
                    "status": "failed",
                    "message": str(error),
                }
            )

        if index < len(product_urls) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    results.extend(discovery_errors)

    failed = sum(
        result["status"] == "failed"
        for result in results
    )

    return {
        "discovered": len(product_urls),
        "created": created,
        "updated": updated,
        "failed": failed,
        "results": results,
    }
