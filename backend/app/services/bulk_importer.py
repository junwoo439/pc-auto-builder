import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.product_importer import (
    extract_product,
    fetch_html,
    read_json_ld,
    type_contains,
    upsert_product,
)


PAGE_DELAY_SECONDS = 1.0
PRODUCT_DELAY_SECONDS = 1.0


PRODUCT_LINK_SELECTORS = [
    '[itemtype*="Product"] a[href]',
    "[data-product-id] a[href]",
    ".product a[href]",
    ".product-item a[href]",
    ".product-card a[href]",
    ".prdList a[href]",
    'a[href*="/product/"]',
    'a[href*="/products/"]',
    'a[href*="/item/"]',
    'a[href*="productDetail"]',
]


NEXT_PAGE_SELECTORS = [
    'a[rel="next"][href]',
    "a.next[href]",
    ".next a[href]",
    ".pagination .next[href]",
    ".pagination .next a[href]",
    ".paging .next[href]",
    ".paging .next a[href]",
    'a[aria-label*="다음"][href]',
    'a[aria-label*="Next"][href]',
]


PAGINATION_CONTAINER_SELECTORS = [
    ".pagination a[href]",
    ".paging a[href]",
    ".page-numbers a[href]",
    ".pager a[href]",
]


def normalize_url(url: str) -> str:
    normalized = url.strip()

    if not normalized.startswith(("http://", "https://")):
        raise ValueError(
            "주소는 http:// 또는 https://로 시작해야 합니다."
        )

    return normalized.split("#")[0]


def same_domain(
    first_url: str,
    second_url: str,
) -> bool:
    return (
        urlparse(first_url).netloc
        == urlparse(second_url).netloc
    )


def looks_like_product_url(url: str) -> bool:
    lowered = url.lower()

    product_patterns = [
        "/product/",
        "/products/",
        "/item/",
        "/goods/",
        "productdetail",
        "product_no=",
        "goodsno=",
        "itemid=",
    ]

    return any(
        pattern in lowered
        for pattern in product_patterns
    )


def looks_like_page_url(
    url: str,
    link_text: str,
) -> bool:
    lowered_url = url.lower()
    lowered_text = link_text.strip().lower()

    page_patterns = [
        r"[?&]page=\d+",
        r"[?&]p=\d+",
        r"[?&]pageindex=\d+",
        r"[?&]pageno=\d+",
        r"/page/\d+",
    ]

    if any(
        re.search(pattern, lowered_url)
        for pattern in page_patterns
    ):
        return True

    if lowered_text in {
        "다음",
        "next",
        ">",
        "›",
        "»",
    }:
        return True

    return lowered_text.isdigit()


def extract_json_ld_product_urls(
    soup: BeautifulSoup,
    page_url: str,
) -> list[str]:
    product_urls: list[str] = []

    for node in read_json_ld(soup):
        if type_contains(node, "Product"):
            candidate = (
                node.get("url")
                or node.get("@id")
            )

            if isinstance(candidate, str):
                product_urls.append(
                    urljoin(page_url, candidate)
                )

        if not type_contains(node, "ItemList"):
            continue

        elements = node.get(
            "itemListElement",
            [],
        )

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

            if isinstance(candidate, str):
                product_urls.append(
                    urljoin(page_url, candidate)
                )

    return product_urls


def extract_product_urls(
    soup: BeautifulSoup,
    page_url: str,
) -> list[str]:
    candidates = extract_json_ld_product_urls(
        soup,
        page_url,
    )

    for selector in PRODUCT_LINK_SELECTORS:
        for link in soup.select(selector):
            href = link.get("href")

            if not href:
                continue

            candidates.append(
                urljoin(page_url, href)
            )

    unique_urls: list[str] = []

    for candidate in candidates:
        clean_url = candidate.split("#")[0]

        if not same_domain(page_url, clean_url):
            continue

        if clean_url == page_url:
            continue

        if clean_url in unique_urls:
            continue

        unique_urls.append(clean_url)

    return unique_urls


def extract_next_page_urls(
    soup: BeautifulSoup,
    page_url: str,
) -> list[str]:
    candidates: list[str] = []

    for selector in NEXT_PAGE_SELECTORS:
        for link in soup.select(selector):
            href = link.get("href")

            if href:
                candidates.append(
                    urljoin(page_url, href)
                )

    for selector in PAGINATION_CONTAINER_SELECTORS:
        for link in soup.select(selector):
            href = link.get("href")

            if not href:
                continue

            absolute_url = urljoin(
                page_url,
                href,
            )

            link_text = link.get_text(
                " ",
                strip=True,
            )

            if looks_like_page_url(
                absolute_url,
                link_text,
            ):
                candidates.append(absolute_url)

    unique_urls: list[str] = []

    for candidate in candidates:
        clean_url = candidate.split("#")[0]

        if not same_domain(page_url, clean_url):
            continue

        if clean_url == page_url:
            continue

        if looks_like_product_url(clean_url):
            continue

        if clean_url in unique_urls:
            continue

        unique_urls.append(clean_url)

    return unique_urls


def collect_product_urls(
    seed_urls: list[str],
    max_pages: int,
    max_products: int,
) -> tuple[
    list[str],
    list[dict[str, str]],
    int,
]:
    page_queue: deque[str] = deque()
    visited_pages: set[str] = set()
    product_urls: list[str] = []
    errors: list[dict[str, str]] = []

    for seed_url in seed_urls:
        normalized = normalize_url(seed_url)

        if normalized not in page_queue:
            page_queue.append(normalized)

    while (
        page_queue
        and len(visited_pages) < max_pages
        and len(product_urls) < max_products
    ):
        page_url = page_queue.popleft()

        if page_url in visited_pages:
            continue

        visited_pages.add(page_url)

        try:
            html = fetch_html(page_url)
            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            found_products = extract_product_urls(
                soup,
                page_url,
            )

            for product_url in found_products:
                if product_url in product_urls:
                    continue

                product_urls.append(product_url)

                if len(product_urls) >= max_products:
                    break

            if len(product_urls) < max_products:
                next_pages = extract_next_page_urls(
                    soup,
                    page_url,
                )

                for next_page in next_pages:
                    if next_page in visited_pages:
                        continue

                    if next_page in page_queue:
                        continue

                    page_queue.append(next_page)

        except Exception as error:
            errors.append(
                {
                    "url": page_url,
                    "message": str(error),
                }
            )

        if page_queue:
            time.sleep(PAGE_DELAY_SECONDS)

    return (
        product_urls,
        errors,
        len(visited_pages),
    )


def import_bulk_products(
    seed_urls: list[str],
    category: str,
    max_pages: int,
    max_products: int,
) -> dict[str, object]:
    (
        product_urls,
        page_errors,
        visited_page_count,
    ) = collect_product_urls(
        seed_urls=seed_urls,
        max_pages=max_pages,
        max_products=max_products,
    )

    results: list[dict[str, object]] = []
    created = 0
    updated = 0
    failed = 0

    for index, product_url in enumerate(product_urls):
        try:
            product = extract_product(
                product_url,
                category,
            )

            action, part_id = upsert_product(
                product
            )

            if action == "created":
                created += 1
            else:
                updated += 1

            results.append(
                {
                    "url": product_url,
                    "status": action,
                    "part_id": part_id,
                    "model_name": product[
                        "model_name"
                    ],
                    "price": product["price"],
                    "message": (
                        "새 부품 추가"
                        if action == "created"
                        else "기존 부품 갱신"
                    ),
                }
            )

        except Exception as error:
            failed += 1

            results.append(
                {
                    "url": product_url,
                    "status": "failed",
                    "message": str(error),
                }
            )

        if index < len(product_urls) - 1:
            time.sleep(PRODUCT_DELAY_SECONDS)

    for page_error in page_errors:
        results.append(
            {
                "url": page_error["url"],
                "status": "page_failed",
                "message": (
                    "목록 페이지 처리 실패: "
                    + page_error["message"]
                ),
            }
        )

    return {
        "visited_pages": visited_page_count,
        "discovered_products": len(product_urls),
        "created": created,
        "updated": updated,
        "failed": failed,
        "page_failed": len(page_errors),
        "results": results,
    }
