from __future__ import annotations

import asyncio
import re
import urllib.parse
from datetime import datetime
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="D2C Search Audit API", version="1.0.0")

# CORS for frontend demo / audit tool
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


class OriginalSearchItem(BaseModel):
    title: str
    price: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None


class EnhancedSearchItem(BaseModel):
    title: str
    price: Optional[str] = None
    image: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    match_type: str = "exact"  # exact | semantic_rewritten | fallback_recommend


class OriginalResults(BaseModel):
    count: int = 0
    items: list[OriginalSearchItem] = Field(default_factory=list)
    has_no_results_message: bool = False
    no_results_text: Optional[str] = None
    error: Optional[str] = None


class EnhancedResults(BaseModel):
    count: int = 0
    items: list[EnhancedSearchItem] = Field(default_factory=list)
    error: Optional[str] = None


class Comparison(BaseModel):
    original_has_results: bool
    enhanced_has_results: bool
    improvement: str


class AuditSearchRequest(BaseModel):
    site_url: str
    query: str
    search_url_pattern: Optional[str] = None


class AuditSearchResponse(BaseModel):
    site_url: str
    query: str
    original_results: OriginalResults
    enhanced_results: EnhancedResults
    comparison: Comparison


class EnhancedSearchRequest(BaseModel):
    query: str
    site_url: Optional[str] = None


class AuditReportRequest(BaseModel):
    site_url: str
    category: str
    market: str
    search_url_pattern: Optional[str] = None


class TestResultItem(BaseModel):
    level: str
    query: str
    original_found: bool
    original_count: int
    enhanced_count: int
    issue: bool
    enhanced_items: list[EnhancedSearchItem] = Field(default_factory=list)


class ScoreInfo(BaseModel):
    current: int
    enhanced: int
    improvement: str
    level: str


class AuditReportResponse(BaseModel):
    site_url: str
    audit_time: str
    score: ScoreInfo
    word_library_estimate: str
    contact_priority: str
    test_results: list[TestResultItem]
    summary: str


# ---------------------------------------------------------------------------
# 增强搜索词库（模拟我们自己的搜索词库 / 向量库）
# ---------------------------------------------------------------------------

ENHANCED_CATALOG: dict[str, list[dict[str, Any]]] = {
    # L1 品牌词（模拟品牌商品池）
    "somethinc": [
        {
            "title": "Somethinc 5% Niacinamide Barrier Serum",
            "price": "Rp 149.000",
            "image": "https://example-cdn.com/somethinc-niacinamide.jpg",
            "tags": ["somethinc", "niacinamide", "barrier"],
            "match_score": 0.97,
        },
        {
            "title": "Somethinc Bakuchiol Skinpair Oil Serum",
            "price": "Rp 189.000",
            "image": "https://example-cdn.com/somethinc-bakuchiol.jpg",
            "tags": ["somethinc", "bakuchiol", "anti aging"],
            "match_score": 0.95,
        },
    ],
    "wardah": [
        {
            "title": "Wardah UV Shield Sunscreen Gel SPF 50",
            "price": "Rp 79.000",
            "image": "https://example-cdn.com/wardah-sunscreen.jpg",
            "tags": ["wardah", "sunscreen", "spf50"],
            "match_score": 0.96,
        },
    ],
    "emina": [
        {
            "title": "Emina Bright Stuff Moisturizer",
            "price": "Rp 59.000",
            "image": "https://example-cdn.com/emina-bright-stuff.jpg",
            "tags": ["emina", "brightening", "moisturizer"],
            "match_score": 0.95,
        },
    ],
    "make over": [
        {
            "title": "Make Over Powerstay Transferproof Matte Lip Cream",
            "price": "Rp 129.000",
            "image": "https://example-cdn.com/makeover-lip-cream.jpg",
            "tags": ["make over", "lip cream", "makeup"],
            "match_score": 0.95,
        },
    ],
    "pixy": [
        {
            "title": "Pixy Make It Glow Dewy Foundation",
            "price": "Rp 89.000",
            "image": "https://example-cdn.com/pixy-foundation.jpg",
            "tags": ["pixy", "foundation", "makeup"],
            "match_score": 0.94,
        },
    ],
    # L2 品类词
    "serum": [
        {
            "title": "Hydrating Serum Hyaluronic Acid",
            "price": "Rp 139.000",
            "image": "https://example-cdn.com/serum-ha.jpg",
            "tags": ["serum", "hyaluronic acid", "hydrating"],
            "match_score": 0.94,
        },
        {
            "title": "Vitamin C Anti Oxidant Serum",
            "price": "Rp 159.000",
            "image": "https://example-cdn.com/serum-vit-c.jpg",
            "tags": ["serum", "vitamin c", "brightening"],
            "match_score": 0.92,
        },
    ],
    "moisturizer": [
        {
            "title": "Ceramide Moisturizer Gel",
            "price": "Rp 119.000",
            "image": "https://example-cdn.com/moisturizer-ceramide.jpg",
            "tags": ["moisturizer", "ceramide", "barrier"],
            "match_score": 0.93,
        },
    ],
    "toner": [
        {
            "title": "AHA BHA Exfoliating Toner",
            "price": "Rp 109.000",
            "image": "https://example-cdn.com/toner-aha-bha.jpg",
            "tags": ["toner", "aha", "bha", "exfoliating"],
            "match_score": 0.93,
        },
    ],
    "sunscreen": [
        {
            "title": "Sunscreen SPF 50 PA++++",
            "price": "Rp 119.000",
            "image": "https://example-cdn.com/sunscreen.jpg",
            "tags": ["sunscreen", "spf50", "protection"],
            "match_score": 0.94,
        },
        {
            "title": "Hydrating UV Essence SPF 30",
            "price": "Rp 99.000",
            "image": "https://example-cdn.com/uv-essence.jpg",
            "tags": ["sunscreen", "spf30", "hydrating"],
            "match_score": 0.91,
        },
    ],
    "cleanser": [
        {
            "title": "Gentle Low pH Cleanser",
            "price": "Rp 79.000",
            "image": "https://example-cdn.com/cleanser-low-ph.jpg",
            "tags": ["cleanser", "low ph", "gentle"],
            "match_score": 0.92,
        },
        {
            "title": "Salicylic Acid Cleanser",
            "price": "Rp 89.000",
            "image": "https://example-cdn.com/cleanser-salicylic.jpg",
            "tags": ["cleanser", "salicylic acid", "jerawat"],
            "match_score": 0.91,
        },
    ],
    # L3 场景/功效词
    "kulit kusam": [
        {
            "title": "Vitamin C Brightening Serum",
            "price": "Rp 159.000",
            "image": "https://example-cdn.com/vitamin-c-serum.jpg",
            "tags": ["brightening", "vitamin c", "glowing", "kulit kusam"],
            "match_score": 0.96,
        },
        {
            "title": "Niacinamide 10% + Zinc 1%",
            "price": "Rp 129.000",
            "image": "https://example-cdn.com/niacinamide.jpg",
            "tags": ["niacinamide", "pori-pori", "kulit kusam", "cerah"],
            "match_score": 0.93,
        },
        {
            "title": "Brightening Moisturizer Gel",
            "price": "Rp 109.000",
            "image": "https://example-cdn.com/brightening-moisturizer.jpg",
            "tags": ["moisturizer", "brightening", "kulit kusam"],
            "match_score": 0.90,
        },
    ],
    "jerawat": [
        {
            "title": "Salicylic Acid 2% Cleanser",
            "price": "Rp 89.000",
            "image": "https://example-cdn.com/salicylic-cleanser.jpg",
            "tags": ["jerawat", "salicylic acid", "acne"],
            "match_score": 0.95,
        },
        {
            "title": "Tea Tree Acne Spot Gel",
            "price": "Rp 75.000",
            "image": "https://example-cdn.com/tea-tree-spot.jpg",
            "tags": ["jerawat", "tea tree", "spot treatment"],
            "match_score": 0.92,
        },
    ],
    "pori-pori": [
        {
            "title": "Pore Minimizing Toner",
            "price": "Rp 115.000",
            "image": "https://example-cdn.com/pore-toner.jpg",
            "tags": ["pori-pori", "pore minimizing", "toner"],
            "match_score": 0.94,
        },
    ],
    "anti aging": [
        {
            "title": "Retinol Anti Aging Night Serum",
            "price": "Rp 199.000",
            "image": "https://example-cdn.com/retinol-serum.jpg",
            "tags": ["anti aging", "retinol", "night serum"],
            "match_score": 0.94,
        },
        {
            "title": "Peptide Firming Moisturizer",
            "price": "Rp 169.000",
            "image": "https://example-cdn.com/peptide-moisturizer.jpg",
            "tags": ["anti aging", "peptide", "firming"],
            "match_score": 0.92,
        },
    ],
    "mencerahkan": [
        {
            "title": "Brightening Vitamin C Serum",
            "price": "Rp 149.000",
            "image": "https://example-cdn.com/brightening-vit-c.jpg",
            "tags": ["mencerahkan", "brightening", "vitamin c"],
            "match_score": 0.95,
        },
    ],
    "default": [
        {
            "title": "Hydrating Facial Cleanser",
            "price": "Rp 99.000",
            "image": "https://example-cdn.com/hydrating-cleanser.jpg",
            "tags": ["cleanser", "hydrating", "daily care"],
            "match_score": 0.70,
        },
        {
            "title": "Sunscreen SPF 50 PA++++",
            "price": "Rp 119.000",
            "image": "https://example-cdn.com/sunscreen.jpg",
            "tags": ["sunscreen", "spf50", "protection"],
            "match_score": 0.68,
        },
    ],
}


# ---------------------------------------------------------------------------
# 审计测试词矩阵
# ---------------------------------------------------------------------------

# L2 品类词：category -> market -> list of category tags
TAG_DICT: dict[str, dict[str, list[str]]] = {
    "beauty": {
        "id": ["serum", "moisturizer", "toner", "sunscreen", "cleanser", "lip cream", "foundation", "masker", "bedak", "eyeshadow"],
        "my": ["serum", "moisturizer", "toner", "sunscreen", "cleanser", "lipstick", "foundation", "mask", "powder"],
        "ph": ["serum", "moisturizer", "toner", "sunscreen", "cleanser", "lip tint", "foundation", "mask", "compact"],
        "sg": ["serum", "moisturizer", "toner", "sunscreen", "cleanser", "lip gloss", "foundation", "mask", "blusher"],
        "vn": ["serum", "moisturizer", "toner", "sunscreen", "cleanser", "son", "foundation", "mask", "phan"],
        "th": ["serum", "moisturizer", "toner", "sunscreen", "cleanser", "lip tint", "foundation", "mask", "powder"],
    },
    "fashion": {
        "id": ["dress", "kaos", "kemeja", "celana", "jaket", "sepatu", "tas", "rok", "hoodie", "sneakers"],
        "my": ["dress", "t-shirt", "shirt", "pants", "jacket", "shoes", "bag", "skirt", "hoodie", "sneakers"],
        "ph": ["dress", "t-shirt", "shirt", "pants", "jacket", "shoes", "bag", "skirt", "hoodie", "sneakers"],
        "sg": ["dress", "t-shirt", "shirt", "pants", "jacket", "shoes", "bag", "skirt", "hoodie", "sneakers"],
        "vn": ["dress", "t-shirt", "shirt", "pants", "jacket", "shoes", "bag", "skirt", "hoodie", "sneakers"],
        "th": ["dress", "t-shirt", "shirt", "pants", "jacket", "shoes", "bag", "skirt", "hoodie", "sneakers"],
    },
    "electronics": {
        "id": ["earphone", "charger", "power bank", "kabel data", "headset", "smartwatch", "speaker", "mouse", "keyboard", "adapter"],
        "my": ["earphone", "charger", "power bank", "cable", "headset", "smartwatch", "speaker", "mouse", "keyboard", "adapter"],
        "ph": ["earphone", "charger", "power bank", "cable", "headset", "smartwatch", "speaker", "mouse", "keyboard", "adapter"],
        "sg": ["earphone", "charger", "power bank", "cable", "headset", "smartwatch", "speaker", "mouse", "keyboard", "adapter"],
        "vn": ["earphone", "charger", "power bank", "cable", "headset", "smartwatch", "speaker", "mouse", "keyboard", "adapter"],
        "th": ["earphone", "charger", "power bank", "cable", "headset", "smartwatch", "speaker", "mouse", "keyboard", "adapter"],
    },
    "home": {
        "id": ["sofa", "kasur", "meja", "kursi", "lampu", "rak", "karpet", "gorden", "hiasan dinding", "tempat tidur"],
        "my": ["sofa", "mattress", "table", "chair", "lamp", "shelf", "carpet", "curtain", "wall decor", "bed"],
        "ph": ["sofa", "mattress", "table", "chair", "lamp", "shelf", "carpet", "curtain", "wall decor", "bed"],
        "sg": ["sofa", "mattress", "table", "chair", "lamp", "shelf", "carpet", "curtain", "wall decor", "bed"],
        "vn": ["sofa", "dem", "ban", "ghe", "den", "ke", "tham", "rem", "trang tri tuong", "giuong"],
        "th": ["sofa", "that", "to", "kao", "lamp", "chan", "phom", "mam", "phad", "tung"],
    },
}

# L3 场景/功效词：market -> tag_type -> canonical -> list of alias_text
ALIAS_MAPPING: dict[str, dict[str, dict[str, list[str]]]] = {
    "id": {
        "function": {
            "kulit kusam": ["wajah kusam", "muka kusam", "tidak glowing", "kusam"],
            "jerawat": ["berjerawat", "acne", "breakout", "bruntusan"],
            "pori-pori": ["pori besar", "pori-pori besar", "pores"],
            "anti aging": ["kerutan", "garis halus", "mencegah penuaan", "anti penuaan"],
            "mencerahkan": ["brightening", "glowing", "cerah", "whitening"],
            "melembapkan": ["hydrating", "lembap", "kulit lembap", "dry skin"],
            "mengontrol minyak": ["oil control", "berminyak", "muka berminyak", "minyak berlebih"],
        },
        "scenario": {
            "kulit berminyak": ["oily skin", "berminyak", "muka berminyak", "minyak berlebih"],
            "kulit kering": ["kering", "kulit kering", "wajah kering", "dry skin"],
            "kulit sensitif": ["sensitif", "kulit sensitif", "iritasi", "sensitive skin"],
            "kulit berjerawat": ["jerawat", "berjerawat", "acne prone", "mudah berjerawat"],
        },
    },
    "my": {
        "function": {
            "dull skin": ["dull skin", "tired skin", "glowing", "brightening"],
            "acne": ["pimples", "breakout", "acne prone"],
            "pores": ["large pores", "open pores", "minimize pores"],
            "anti aging": ["wrinkles", "fine lines", "anti ageing"],
            "hydrating": ["hydration", "moisturizing", "dry skin"],
        },
        "scenario": {
            "oily skin": ["oily skin", "shiny face", "excess oil"],
            "dry skin": ["dry skin", "flaky skin", "dehydrated"],
            "sensitive skin": ["sensitive skin", "irritated skin", "redness"],
        },
    },
    "ph": {
        "function": {
            "dull skin": ["dull skin", "tired skin", "glowing", "brightening"],
            "acne": ["pimples", "breakout", "acne prone"],
            "pores": ["large pores", "open pores"],
            "anti aging": ["wrinkles", "fine lines"],
            "hydrating": ["hydration", "moisturizing", "dry skin"],
        },
        "scenario": {
            "oily skin": ["oily skin", "shiny face"],
            "dry skin": ["dry skin", "flaky skin"],
            "sensitive skin": ["sensitive skin", "irritated skin"],
        },
    },
    "sg": {
        "function": {
            "dull skin": ["dull skin", "tired skin", "glowing", "brightening"],
            "acne": ["pimples", "breakout", "acne prone"],
            "pores": ["large pores", "open pores"],
            "anti aging": ["wrinkles", "fine lines"],
            "hydrating": ["hydration", "moisturizing", "dry skin"],
        },
        "scenario": {
            "oily skin": ["oily skin", "shiny face"],
            "dry skin": ["dry skin", "flaky skin"],
            "sensitive skin": ["sensitive skin", "irritated skin"],
        },
    },
    "vn": {
        "function": {
            "dull skin": ["da xam xit", "sang da", "brightening"],
            "acne": ["mun", "da mun", "breakout"],
            "pores": ["lo chan long to", "pores"],
            "anti aging": ["chong lao hoa", "nan nhan"],
            "hydrating": ["cap am", "duong am", "da kho"],
        },
        "scenario": {
            "oily skin": ["da dau", "dau nhon"],
            "dry skin": ["da kho", "kho rao"],
            "sensitive skin": ["da nhay cam", "kich ung"],
        },
    },
    "th": {
        "function": {
            "dull skin": ["ผิวหมองคล้ำ", "glowing", "brightening"],
            "acne": ["สิว", "breakout", "acne prone"],
            "pores": ["รูขุมขนกว้าง", "pores"],
            "anti aging": ["ต่อต้านริ้วรอย", "wrinkles"],
            "hydrating": ["hydration", "ชุ่มชื้น", "dry skin"],
        },
        "scenario": {
            "oily skin": ["ผิวมัน", "oily skin"],
            "dry skin": ["ผิวแห้ง", "dry skin"],
            "sensitive skin": ["ผิวแพ้ง่าย", "sensitive skin"],
        },
    },
}

# L1 通用品牌词兜底（当自动提取失败时使用）
DEFAULT_BRAND_WORDS: dict[str, dict[str, list[str]]] = {
    "beauty": {
        "id": ["Somethinc", "Wardah", "Emina", "Make Over", "Pixy"],
        "my": ["SK-II", "L'Oreal", "Maybelline", "Innisfree", "Kiehl's"],
        "ph": ["Maybelline", "L'Oreal", "Vice Cosmetics", "Happy Skin", "Careline"],
        "sg": ["SK-II", "L'Oreal", "Innisfree", "Kiehl's", "The Ordinary"],
        "vn": ["Innisfree", "L'Oreal", "Some By Mi", "Cocoon", "The Body Shop"],
        "th": ["L'Oreal", "Innisfree", "Mistine", "Cute Press", "Srichand"],
    },
    "fashion": {
        "id": ["Zara", "H&M", "Uniqlo", "Pull&Bear", "Cotton On"],
        "my": ["Zara", "H&M", "Uniqlo", "Cotton On", "Pomelo"],
        "ph": ["Zara", "H&M", "Uniqlo", "Cotton On", "Pomelo"],
        "sg": ["Zara", "H&M", "Uniqlo", "Cotton On", "Pomelo"],
        "vn": ["Zara", "H&M", "Uniqlo", "Cotton On", "Canifa"],
        "th": ["Zara", "H&M", "Uniqlo", "Cotton On", "Pomelo"],
    },
    "electronics": {
        "id": ["Samsung", "Xiaomi", "Oppo", "Vivo", "Realme"],
        "my": ["Samsung", "Xiaomi", "Oppo", "Vivo", "Realme"],
        "ph": ["Samsung", "Xiaomi", "Oppo", "Vivo", "Realme"],
        "sg": ["Samsung", "Xiaomi", "Apple", "Sony", "Bose"],
        "vn": ["Samsung", "Xiaomi", "Oppo", "Vivo", "Apple"],
        "th": ["Samsung", "Xiaomi", "Oppo", "Vivo", "Apple"],
    },
    "home": {
        "id": ["IKEA", "Informa", "Fabelio", "Dekoruma", "Athaya"],
        "my": ["IKEA", "Kaison", "MR DIY", "HOOGA", "Nitori"],
        "ph": ["IKEA", "Mandaue Foam", "Our Home", "Dimensione", "Solen"],
        "sg": ["IKEA", "Courts", "FortyTwo", "HipVan", "Castlery"],
        "vn": ["IKEA", "Nha Xinh", "UMA", "Go Home", "AConcept"],
        "th": ["IKEA", "SB Design Square", "Index Living Mall", "Modernform", "Chanitr"],
    },
}

NO_RESULTS_KEYWORDS = [
    "no results",
    "tidak ditemukan",
    "not found",
    "no products",
    "未找到",
    "找不到",
    "maaf",
    "produk tidak",
    "0 hasil",
    "zero results",
]

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1"
)


# ---------------------------------------------------------------------------
# 内部增强搜索函数（供 /api/search 和 /api/audit/search 共用）
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def perform_enhanced_search(query: str, site_url: Optional[str] = None) -> EnhancedResults:
    """
    内部函数调用：基于查询词匹配词库，返回增强搜索结果。
    不经过 HTTP，直接在内存/进程内返回。
    """
    try:
        normalized_query = _normalize(query)
        results: list[dict[str, Any]] = []

        # L3 场景/功效词：命中这些 key 时视为语义改写，而非精确匹配
        SEMANTIC_KEYS = {"kulit kusam", "jerawat", "pori-pori", "anti aging", "mencerahkan"}

        # 1. 精确词库匹配
        for key, items in ENHANCED_CATALOG.items():
            if key == "default":
                continue
            normalized_key = _normalize(key)
            if normalized_key in normalized_query or normalized_query in normalized_key:
                key_match_type = "semantic_rewritten" if key in SEMANTIC_KEYS else "exact"
                for item in items:
                    copy_item = dict(item)
                    copy_item["match_type"] = key_match_type
                    results.append(copy_item)

        # 2. 如果没有命中，按关键词标签模糊匹配
        if not results:
            query_tokens = set(normalized_query.split())
            for key, items in ENHANCED_CATALOG.items():
                if key == "default":
                    continue
                for item in items:
                    tags = {_normalize(t) for t in item.get("tags", [])}
                    if query_tokens & tags:
                        # 复制并调低分数
                        copy_item = dict(item)
                        copy_item["match_score"] = round(max(0.60, copy_item.get("match_score", 0.7) - 0.15), 2)
                        copy_item["match_type"] = "semantic_rewritten"
                        results.append(copy_item)

        # 3. 去重
        seen_titles: set[str] = set()
        unique_results: list[dict[str, Any]] = []
        for item in results:
            title = item.get("title")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_results.append(item)

        # 4. 兜底默认结果
        if not unique_results:
            unique_results = [
                dict(item, match_type="fallback_recommend")
                for item in ENHANCED_CATALOG.get("default", [])
            ]

        # 确保所有结果都带有 match_type
        for item in unique_results:
            item.setdefault("match_type", "exact")

        return EnhancedResults(
            count=len(unique_results),
            items=[EnhancedSearchItem(**item) for item in unique_results[:10]],
        )
    except Exception as exc:  # pragma: no cover
        return EnhancedResults(error=f"增强搜索处理失败: {exc}", count=0)


# ---------------------------------------------------------------------------
# 路由：增强搜索 API
# ---------------------------------------------------------------------------


@app.post("/api/search", response_model=EnhancedResults)
async def search_enhanced(req: EnhancedSearchRequest) -> EnhancedResults:
    """
    我们自己的搜索增强 API。基于本地词库返回相关商品。
    """
    return perform_enhanced_search(req.query, req.site_url)


# ---------------------------------------------------------------------------
# 搜索 URL 自动发现
# ---------------------------------------------------------------------------


async def discover_search_url(site_url: str, query: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    尝试请求首页并自动发现搜索 URL。
    优先级：
      1. HTML 中的搜索表单 action
      2. 常见的搜索 URL 模式（HEAD 探测）
    """
    encoded_query = urllib.parse.quote(query)
    base = site_url.rstrip("/")

    # 1. 解析首页搜索表单
    try:
        resp = await client.get(site_url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        form = (
            soup.find("form", attrs={"role": "search"})
            or soup.find("form", class_=re.compile("search", re.I))
            or soup.find("form", action=re.compile("search|catalogsearch|result", re.I))
        )
        if isinstance(form, BeautifulSoup) or form is None:
            form = None
        if form and form.get("action"):
            action = urllib.parse.urljoin(site_url, str(form["action"]))
            input_field = (
                form.find("input", attrs={"type": "search"})
                or form.find("input", attrs={"type": "text"})
                or form.find("input", attrs={"name": re.compile(r"q|s|search|keyword", re.I)})
            )
            param_name = input_field.get("name", "q") if input_field else "q"
            return f"{action}?{param_name}={encoded_query}"
    except Exception:
        # 首页访问失败也不中断，继续尝试常见模式
        pass

    # 2. 常见搜索 URL 模式 HEAD 探测
    candidates = [
        f"{base}/search?q={encoded_query}",
        f"{base}/search/{encoded_query}",
        f"{base}/?s={encoded_query}",
        f"{base}/catalogsearch/result/?q={encoded_query}",
        f"{base}/search/results?q={encoded_query}",
    ]

    for url in candidates:
        try:
            r = await client.head(url, timeout=5.0, follow_redirects=True)
            if r.status_code < 400:
                return url
        except Exception:
            continue

    return None


# ---------------------------------------------------------------------------
# 原站搜索结果解析
# ---------------------------------------------------------------------------


def _extract_text(element: Any) -> Optional[str]:
    if element is None:
        return None
    return element.get_text(strip=True)


def _extract_price(element: Any) -> Optional[str]:
    if element is None:
        return None
    text = element.get_text(strip=True)
    # 优先匹配货币前缀（如 Rp 159.000），其次匹配数字后缀（如 159.000 USD）
    match = re.search(
        r"[A-Z]{1,3}\s*[\d.,]+(?:\s*[A-Z]{0,3})|[\d.,]+(?:\s*[A-Z]{1,3})",
        text,
    )
    return match.group(0).strip() if match else text


def _extract_image(el: BeautifulSoup, base_url: str) -> Optional[str]:
    img = el.find("img")
    if not img:
        return None
    for attr in ("src", "data-src", "data-lazy-src", "data-original", "srcset"):
        value = img.get(attr)
        if value:
            if attr == "srcset":
                value = value.split(",")[0].strip().split(" ")[0]
            return urllib.parse.urljoin(base_url, str(value))
    return None


def _extract_item_url(el: BeautifulSoup, base_url: str) -> Optional[str]:
    link = el.find("a", href=True)
    if link:
        return urllib.parse.urljoin(base_url, str(link["href"]))
    return None


def _extract_item_from_element(el: BeautifulSoup, base_url: str) -> Optional[dict[str, Any]]:
    """从单个商品 DOM 元素中提取信息。"""
    title: Optional[str] = None
    url: Optional[str] = None

    # 优先从标题标签/链接里取标题
    for selector in ["h1", "h2", "h3", "h4", ".product-title", ".product-name", ".title", ".name"]:
        title_el = el.select_one(selector)
        if title_el:
            title = _extract_text(title_el)
            if title_el.name == "a":
                url = urllib.parse.urljoin(base_url, str(title_el.get("href", "")))
            break

    # 如果没标题，尝试图片 alt 文本
    if not title:
        img = el.find("img")
        if img and img.get("alt"):
            title = str(img["alt"]).strip()

    if not title:
        return None

    if not url:
        url = _extract_item_url(el, base_url)

    # 价格
    price: Optional[str] = None
    for selector in [
        ".price",
        ".product-price",
        ".current-price",
        ".amount",
        ".sale-price",
        "[class*='price']",
        ".harga",
    ]:
        price_el = el.select_one(selector)
        if price_el:
            price = _extract_price(price_el)
            if price:
                break

    image = _extract_image(el, base_url)

    return {
        "title": title,
        "price": price,
        "image": image,
        "url": url,
    }


def parse_search_results(html: str, base_url: str) -> OriginalResults:
    """解析 D2C 网站搜索结果 HTML。"""
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True)
    page_text_lower = page_text.lower()

    has_no_results = False
    no_results_text: Optional[str] = None

    for keyword in NO_RESULTS_KEYWORDS:
        if keyword.lower() in page_text_lower:
            has_no_results = True
            # 尝试提取包含该关键词的短句
            match = re.search(
                rf"[^.!?]*?{re.escape(keyword)}[^.!?]*[.!?]?",
                page_text,
                re.IGNORECASE,
            )
            no_results_text = (match.group(0).strip() if match else keyword).strip()
            break

    # 尝试提取结果数量
    count = 0
    count_patterns = [
        r"([\d.,]+)\s*(?:results?|produk|items?|products?|ditemukan|found|hasil|rezultate)",
        r"(?:results?|produk|items?|products?|ditemukan|found|hasil|rezultate)\s*[:\-]?\s*([\d.,]+)",
        r"([\d.,]+)\s*(?:total|menampilkan)",
    ]
    for pattern in count_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "").replace(".", "")
            try:
                count = int(raw)
                break
            except ValueError:
                continue

    # 提取结果列表
    items: list[dict[str, Any]] = []
    selectors = [
        "article.product",
        ".product-item",
        ".search-item",
        ".item.product",
        ".product-card",
        "[data-product]",
        ".search-result",
        ".ais-Hits-item",
        ".item-product",
        ".product-list-item",
        ".grid-item",
        ".plp-item",
        ".sku-item",
        ".c-product-card",
    ]

    for selector in selectors:
        elements = soup.select(selector)
        if elements:
            for el in elements:
                item = _extract_item_from_element(el, base_url)
                if item and item.get("title"):
                    items.append(item)
                if len(items) >= 5:
                    break
            break

    # 兜底：如果没找到结构化元素，尝试从含 product/produk/p/ 的链接提取
    if not items:
        seen_urls: set[str] = set()
        for link in soup.find_all("a", href=True):
            href = str(link["href"]).lower()
            if any(marker in href for marker in ["/product", "/produk", "/p/", "/item/", "/products/"]):
                abs_url = urllib.parse.urljoin(base_url, str(link["href"]))
                if abs_url in seen_urls:
                    continue
                seen_urls.add(abs_url)
                title = _extract_text(link) or link.get("title") or link.get("aria-label")
                if title:
                    items.append({
                        "title": str(title).strip(),
                        "price": None,
                        "image": None,
                        "url": abs_url,
                    })
                if len(items) >= 5:
                    break

    # 截断到最多 5 条
    items = items[:5]

    # 如果数量解析失败但确实有商品，用商品数量作为 count
    if count == 0 and items:
        count = len(items)

    return OriginalResults(
        count=count,
        items=[OriginalSearchItem(**item) for item in items],
        has_no_results_message=has_no_results,
        no_results_text=no_results_text,
    )


# ---------------------------------------------------------------------------
# 审计报告：测试词提取与分数计算
# ---------------------------------------------------------------------------


# 品牌提取时应过滤的常见噪音词
BRAND_NOISE_WORDS = {
    "demo", "store", "shop", "official", "home", "welcome", "online", "best",
    "buy", "sale", "new", "site", "website", "cart", "bag", "account", "login",
    "search", "menu", "about", "contact", "help", "faq", "terms", "privacy",
    "shipping", "returns", "order", "track", "wishlist", "collection", "catalog",
    "products", "produk", "barang", "toko", "butik", "boutique", "product",
    "detail", "item", "page", "category", "brand", "nama", "title", "logo",
    "image", "img", "icon", "banner", "slide", "thumbnail", "picture",
}


def _clean_brand_name(text: str) -> Optional[str]:
    """从 title/footer/logo 文本中提取候选品牌名。"""
    text = text.strip()
    if not text:
        return None
    # 在常见分隔符/结束词处截断
    for splitter in [" | ", " - ", " — ", " : ", " |", " -", " —", " :",
                     "Official", "Store", "Shop", "Home", "Online", "Indonesia"]:
        if splitter in text:
            text = text.split(splitter)[0].strip()
    # 移除末尾标点
    text = re.sub(r"[^\w\s&]+$", "", text).strip()
    if len(text) >= 2 and text.lower() not in BRAND_NOISE_WORDS:
        return text
    return None


async def extract_brand_words(
    site_url: str,
    client: httpx.AsyncClient,
    category: str,
    market: str,
) -> list[str]:
    """
    尝试从首页和热门产品页自动提取品牌词/高频产品词。
    如果自动提取失败，返回该品类+市场的通用测试品牌词。
    """
    candidates: list[str] = []
    try:
        resp = await client.get(site_url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. 从 footer 版权信息提取（通常最准确）
        footer = soup.find("footer")
        if footer:
            footer_text = footer.get_text(separator=" ", strip=True)
            # 匹配 "© 2024 BrandName" 或 "© BrandName"
            match = re.search(
                r"©\s*\d{0,4}\s*([A-Z][A-Za-z0-9\s&'\.]+?)(?:\.|\s+All\s+rights|\s+Copyright|\s+Ltd|\s+Inc|\s+LLC|$)",
                footer_text,
                re.IGNORECASE,
            )
            if match:
                brand = _clean_brand_name(match.group(1))
                if brand:
                    candidates.append(brand)

        # 2. 从 logo 图片 alt 文本提取（只取首个片段作为品牌名）
        for img in soup.find_all("img"):
            alt = str(img.get("alt", "")).strip()
            if alt and 2 <= len(alt) < 50:
                # 如果 alt 是完整标题，只取第一个词
                first_word = alt.split()[0]
                brand = _clean_brand_name(first_word)
                if brand:
                    candidates.append(brand)

        # 3. 从 <title> 提取品牌名（取分隔符前部分）
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            brand = _clean_brand_name(title_text)
            if brand:
                candidates.append(brand)

        # 4. 从热门产品页标题提取第一个大写词（通常是品牌）
        product_links: list[str] = []
        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if any(marker in href.lower() for marker in ["/product", "/produk", "/p/", "/item/", "/products/"]):
                abs_url = urllib.parse.urljoin(site_url, href)
                if abs_url not in product_links:
                    product_links.append(abs_url)
                if len(product_links) >= 3:
                    break

        for url in product_links[:2]:
            try:
                p_resp = await client.get(url, timeout=8.0, follow_redirects=True)
                p_resp.raise_for_status()
                p_soup = BeautifulSoup(p_resp.text, "html.parser")
                h1 = p_soup.find("h1")
                if h1:
                    text = h1.get_text(strip=True)
                    words = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text)
                    for w in words[:1]:
                        brand = _clean_brand_name(w)
                        if brand:
                            candidates.append(brand)
                            break
            except Exception:
                continue

        # 5. 去重并过滤噪音（移除空格后比较小写，避免 "DemoBeauty"/"Demo Beauty" 重复）
        seen: set[str] = set()
        result: list[str] = []
        for c in candidates:
            c = c.strip()
            key = re.sub(r"\s+", "", c.lower())
            if len(c) >= 2 and key not in seen and key not in BRAND_NOISE_WORDS and not key.startswith("http"):
                seen.add(key)
                result.append(c)
            if len(result) >= 5:
                break

        # 6. 如果自动提取不足 3 个，用通用品牌词补充到 5 个
        if len(result) >= 3:
            return result[:5]

        defaults = DEFAULT_BRAND_WORDS.get(category, {}).get(
            market,
            ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E"],
        )
        for brand in defaults:
            key = re.sub(r"\s+", "", brand.lower())
            if key not in seen and key not in BRAND_NOISE_WORDS:
                seen.add(key)
                result.append(brand)
            if len(result) >= 5:
                break
        return result[:5]
    except Exception:
        # 自动提取失败，回退到通用品牌词
        pass

    return DEFAULT_BRAND_WORDS.get(category, {}).get(
        market,
        ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E"],
    )[:5]


def select_test_words(category: str, market: str, brand_words: list[str]) -> list[tuple[str, str]]:
    """
    根据 category 和 market 选择 L1/L2/L3 测试词。
    返回 [(level, query), ...]。
    """
    results: list[tuple[str, str]] = []

    # L1 品牌词（3-5 个）
    for word in brand_words[:5]:
        results.append(("L1", word))

    # L2 品类词（5 个）
    category_words = TAG_DICT.get(category, {}).get(market, [])
    for word in category_words[:5]:
        results.append(("L2", word))

    # L3 场景/功效词 alias（5 个）
    market_aliases = ALIAS_MAPPING.get(market, {})
    alias_texts: list[str] = []
    for tag_type in ["function", "scenario"]:
        for canonical, aliases in market_aliases.get(tag_type, {}).items():
            if aliases:
                alias_texts.append(aliases[0])
            if len(alias_texts) >= 5:
                break
        if len(alias_texts) >= 5:
            break

    for word in alias_texts[:5]:
        results.append(("L3", word))

    return results


def calculate_scores(test_results: list[TestResultItem]) -> tuple[int, int, str, str]:
    """计算当前分数、增强后分数、提升幅度和等级。"""
    current = 100
    enhanced = 100

    for r in test_results:
        if r.level == "L1" and not r.original_found:
            current -= 30
            if r.enhanced_count == 0:
                enhanced -= 30
        elif r.level == "L2" and not r.original_found:
            current -= 10
            if r.enhanced_count == 0:
                enhanced -= 10
        elif r.level == "L3" and not r.original_found:
            current -= 5
            if r.enhanced_count == 0:
                enhanced -= 5

    current = max(0, current)
    enhanced = max(0, enhanced)
    improvement = enhanced - current

    if current >= 80:
        level = "excellent"
    elif current >= 60:
        level = "good"
    elif current >= 40:
        level = "fair"
    else:
        level = "poor"

    return current, enhanced, f"{improvement:+d}", level


def estimate_word_library_need(test_results: list[TestResultItem]) -> str:
    """根据未命中情况预估词库需求等级。"""
    l3_results = [r for r in test_results if r.level == "L3"]
    l2_results = [r for r in test_results if r.level == "L2"]

    l3_missing_count = sum(1 for r in l3_results if not r.original_found)
    l2_missing_count = sum(1 for r in l2_results if not r.original_found)

    if l3_results and l3_missing_count >= len(l3_results) / 2:
        return "high"
    if l2_missing_count > 0:
        return "medium"
    return "low"


def calculate_contact_priority(current: int, enhanced: int) -> str:
    """根据可提升幅度判断联系优先级。"""
    improvement = enhanced - current
    if improvement >= 40:
        return "high"
    if improvement >= 20:
        return "medium"
    return "low"


def generate_summary(test_results: list[TestResultItem], current: int, enhanced: int) -> str:
    """生成通顺、有说服力的审计摘要。"""
    total = len(test_results)
    missing = sum(1 for r in test_results if not r.original_found)
    l1_missing = sum(1 for r in test_results if r.level == "L1" and not r.original_found)
    l2_missing = sum(1 for r in test_results if r.level == "L2" and not r.original_found)
    l3_missing = sum(1 for r in test_results if r.level == "L3" and not r.original_found)

    parts = [f"测试 {total} 个词，{missing} 个原站搜不到。"]

    if l1_missing > 0:
        parts.append(f"其中 {l1_missing} 个品牌词（L1）搜不到，属于高危流失场景。")
    if l2_missing > 0:
        parts.append(f"{l2_missing} 个品类词（L2）搜不到，影响类目引流。")
    if l3_missing > 0:
        parts.append(f"{l3_missing} 个场景/功效词（L3）搜不到，这是用户最核心的痛点表达。")

    parts.append(f"接入增强搜索后，预计搜索健康度从 {current} 分提升到 {enhanced} 分。")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# 路由：搜索审计接口
# ---------------------------------------------------------------------------


@app.post("/api/audit/search", response_model=AuditSearchResponse)
async def audit_search(req: AuditSearchRequest) -> AuditSearchResponse:
    """
    代理目标 D2C 网站搜索，并和我们自己的增强搜索做对比。
    """
    site_url = req.site_url.strip()
    query = req.query.strip()

    headers = {"User-Agent": MOBILE_USER_AGENT}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        # 1. 构造原站搜索 URL
        if req.search_url_pattern:
            original_search_url = req.search_url_pattern.replace("{query}", urllib.parse.quote(query))
        else:
            discovered = await discover_search_url(site_url, query, client)
            if not discovered:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "请提供 search_url_pattern 参数"},
                )
            original_search_url = discovered

        # 2. 代理请求原站
        try:
            resp = await client.get(original_search_url, timeout=10.0)
            resp.raise_for_status()
            original_results = parse_search_results(resp.text, site_url)
        except httpx.TimeoutException:
            original_results = OriginalResults(
                count=0,
                error="请求目标网站超时（10 秒）",
            )
        except httpx.HTTPStatusError as exc:
            original_results = OriginalResults(
                count=0,
                error=f"目标网站返回错误状态码: {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            original_results = OriginalResults(
                count=0,
                error=f"无法访问目标网站: {exc}",
            )
        except Exception as exc:
            original_results = OriginalResults(
                count=0,
                error=f"无法访问目标网站: {exc}",
            )

    # 3. 调用我们自己的增强搜索（内部函数调用，不经过 HTTP）
    enhanced_results = perform_enhanced_search(query, site_url)

    # 4. 构造对比结果
    original_has_results = (
        original_results.error is None
        and original_results.count > 0
        and len(original_results.items) > 0
        and not original_results.has_no_results_message
    )
    enhanced_has_results = enhanced_results.count > 0 and len(enhanced_results.items) > 0

    if original_has_results and enhanced_has_results:
        improvement = f"原站有 {original_results.count} 个结果，增强搜索提供 {enhanced_results.count} 个结果"
    elif original_has_results and not enhanced_has_results:
        improvement = f"原站有 {original_results.count} 个结果，增强搜索无结果"
    elif not original_has_results and enhanced_has_results:
        improvement = f"从 {original_results.count} 个结果提升到 {enhanced_results.count} 个结果"
    else:
        improvement = "双方均无搜索结果"

    return AuditSearchResponse(
        site_url=site_url,
        query=query,
        original_results=original_results,
        enhanced_results=enhanced_results,
        comparison=Comparison(
            original_has_results=original_has_results,
            enhanced_has_results=enhanced_has_results,
            improvement=improvement,
        ),
    )


# ---------------------------------------------------------------------------
# 路由：完整审计报告
# ---------------------------------------------------------------------------


@app.post("/api/audit/report", response_model=AuditReportResponse)
async def audit_report(req: AuditReportRequest) -> AuditReportResponse:
    """
    对目标网站执行完整审计（L1 品牌词、L2 品类词、L3 场景/功效词），
    生成综合审计报告。
    """
    site_url = req.site_url.strip()
    category = req.category.lower()
    market = req.market.lower()
    audit_time = datetime.now().isoformat()

    headers = {"User-Agent": MOBILE_USER_AGENT}

    # 1. 自动提取品牌词（L1）
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        brand_words = await extract_brand_words(site_url, client, category, market)

    # 2. 选择测试词
    test_words = select_test_words(category, market, brand_words)

    # 3. 对每个测试词调用 /api/audit/search（内部函数调用）
    test_results: list[TestResultItem] = []
    for level, query in test_words:
        audit_req = AuditSearchRequest(
            site_url=site_url,
            query=query,
            search_url_pattern=req.search_url_pattern,
        )
        audit_resp = await audit_search(audit_req)

        original_found = audit_resp.comparison.original_has_results
        original_count = audit_resp.original_results.count
        enhanced_count = audit_resp.enhanced_results.count
        issue = not original_found and enhanced_count > 0

        test_results.append(
            TestResultItem(
                level=level,
                query=query,
                original_found=original_found,
                original_count=original_count,
                enhanced_count=enhanced_count,
                issue=issue,
                enhanced_items=audit_resp.enhanced_results.items if issue else [],
            )
        )

    # 4. 计算分数、需求预估和优先级
    current, enhanced, improvement, level = calculate_scores(test_results)
    word_library_estimate = estimate_word_library_need(test_results)
    contact_priority = calculate_contact_priority(current, enhanced)
    summary = generate_summary(test_results, current, enhanced)

    return AuditReportResponse(
        site_url=site_url,
        audit_time=audit_time,
        score=ScoreInfo(
            current=current,
            enhanced=enhanced,
            improvement=improvement,
            level=level,
        ),
        word_library_estimate=word_library_estimate,
        contact_priority=contact_priority,
        test_results=test_results,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# 路由：提交报告请求（留资）
# ---------------------------------------------------------------------------


class AuditContactRequest(BaseModel):
    email: str
    site_url: Optional[str] = None
    score: Optional[dict[str, Any]] = None
    word_library_estimate: Optional[str] = None
    test_results: Optional[list[dict[str, Any]]] = None
    summary: Optional[str] = None


@app.post("/api/audit/contact")
async def audit_contact(req: AuditContactRequest) -> dict[str, str]:
    """
    接收用户邮箱及审计报告数据，用于后续发送完整报告。
    生产环境中可接入邮件服务（SendGrid / AWS SES / Resend）。
    """
    # 这里仅做接收确认；真实场景下可将报告数据写入数据库或发送邮件
    return {
        "status": "ok",
        "message": "Report request received. We'll email you the full report shortly.",
    }


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
