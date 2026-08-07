import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from app.data.database import connect_database


USER_AGENT = "PC-Auto-Builder/1.0"
REQUEST_DELAY_SECONDS = 1.0
TIMEOUT_SECONDS = 15


def normalize_url(url: str) -> str:
    normalized = url.strip()

    if not normalized.startswith(("http://", "https://")):
        raise ValueError("http:// 또는 https://로 시작해야 합니다.")

    return normalized


def robots_allows(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    robots_url = (
        f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    )

    try:
        response = requests.get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
    except requests.RequestException:
        return False, "robots.txt를 확인하지 못했습니다."

    if response.status_code == 404:
        return True, ""

    if not response.ok:
        return False, (
            f"robots.txt 확인 실패: "
            f"HTTP {response.status_code}"
        )

    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())

    if not parser.can_fetch(USER_AGENT, url):
        return False, "robots.txt에서 수집을 허용하지 않습니다."

    return True, ""


def fetch_html(url: str) -> str:
    allowed, reason = robots_allows(url)

    if not allowed:
        raise ValueError(reason)

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
        timeout=TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    )

    if "text/html" not in content_type:
        raise ValueError("HTML 페이지가 아닙니다.")

    return response.text


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


def upsert_product(
    product: dict[str, object],
) -> tuple[str, int]:
    specifications = product["specifications"]

    if not isinstance(specifications, dict):
        raise ValueError("제품 규격 형식이 잘못되었습니다.")

    source_url = str(
        specifications.get("source_url", "")
    )

    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                manufacturer,
                model_name,
                specifications
            FROM parts
            """
        ).fetchall()

        existing_id: int | None = None
        old_specifications: dict[str, object] = {}

        for row in rows:
            try:
                row_specs = json.loads(
                    row["specifications"]
                )
            except json.JSONDecodeError:
                row_specs = {}

            same_source = (
                row_specs.get("source_url")
                == source_url
            )

            same_name = (
                str(row["manufacturer"]).lower()
                == str(product["manufacturer"]).lower()
                and str(row["model_name"]).lower()
                == str(product["model_name"]).lower()
            )

            if same_source or same_name:
                existing_id = int(row["id"])
                old_specifications = row_specs
                break

        merged_specs = {
            **old_specifications,
            **specifications,
        }

        serialized_specs = json.dumps(
            merged_specs,
            ensure_ascii=False,
        )

        if existing_id is not None:
            connection.execute(
                """
                UPDATE parts
                SET
                    category = ?,
                    manufacturer = ?,
                    model_name = ?,
                    price = ?,
                    specifications = ?
                WHERE id = ?
                """,
                (
                    product["category"],
                    product["manufacturer"],
                    product["model_name"],
                    product["price"],
                    serialized_specs,
                    existing_id,
                ),
            )

            connection.commit()

            return "updated", existing_id

        cursor = connection.execute(
            """
            INSERT INTO parts (
                category,
                manufacturer,
                model_name,
                price,
                specifications
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product["category"],
                product["manufacturer"],
                product["model_name"],
                product["price"],
                serialized_specs,
            ),
        )

        connection.commit()

        return "created", int(cursor.lastrowid)


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
