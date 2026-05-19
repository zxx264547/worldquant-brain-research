# -*- coding: utf-8 -*-
"""
seed_alpha_generator.py — Alpha 表达式生成器
功能：
  - 登录 WorldQuant BRAIN 平台
  - 抓取指定数据集的字段、操作符
  - 使用 arXiv + Semantic Scholar 两级论文预搜索为 LLM 提供真实学术依据
  - 通过 OpenAI / Anthropic 双适配调用 LLM 生成 feature idea
  - 解析 Concept 块、标准化占位符、展开为可执行的 Alpha 表达式
  - 在命令行直接输出最终表达式清单
使用方式：
  1. 在下方「运行配置」区段填入 BRAIN 账号、地区、delay、宇宙、数据集、AI URL/KEY/MODEL
  2. 运行：python seed_alpha_generator.py
  3. 终端会依次打印 Idea 报告与最终表达式
依赖：
  pip install requests pandas
"""
from __future__ import annotations
import itertools
import json
import logging
import os
import re
import sys
import time

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus, urljoin
import pandas as pd
import requests
# =============================================================================
# 运行配置区（在此修改所有参数，无需命令行传参）
# =============================================================================
# ---- BRAIN 平台账号 ----
BRAIN_EMAIL = "2645471525@qq.com"
BRAIN_PASSWORD = "20001025ZHANG"
BRAIN_API_URL = "https://api.worldquantbrain.com"
# ---- 回测设置 ----
INSTRUMENT_TYPE = "EQUITY"
REGION = "USA"                                # USA / GLB / EUR / ASI / CHN / JPN / KOR / HKG / IND / AMR ...
DELAY = 1                                     # 0 或 1
UNIVERSE = "TOP3000"                          # TOP3000 / TOP1000 / TOP500 ...
DATA_TYPE = "MATRIX"                          # MATRIX 或 VECTOR
DATASET_ID = "analyst47"                      # 目标数据集 ID (复合Alpha指标)
DATA_CATEGORY = ""                            # 留空则按 DATASET_ID 前缀自动推断
# ---- AI 模型接入 (DeepSeek via Anthropic) ----
AI_BASE_URL = "https://api.deepseek.com/anthropic"
AI_API_KEY = "sk-a1fc85c5a72a40c4b99aab96add4fa48"
AI_MODEL = "deepseek-v4-pro[1m]"
AI_TIMEOUT_SECONDS = 300
# ---- 论文搜索设置 ----
PAPER_MAX_QUERIES = 6
PAPER_PER_QUERY = 5
PAPER_YEAR_FROM = 2020
PAPER_TIMEOUT_SECONDS = 30
# ---- 种子生成参数 ----
MAX_ALLOWED_OPERATORS_IN_PROMPT = 300
MAX_PRIMARY_CANDIDATES = 30
MAX_SECONDARY_CHOICES = 8
MAX_EXPRESSIONS_PER_TEMPLATE = 5000
# ---- 输出目录 ----
OUTPUT_DIR = Path(__file__).resolve().parent / "seed_output"

# =============================================================================
# 日志
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)
log = logging.getLogger("seed-gen")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# =============================================================================
# BRAIN REST 客户端
# =============================================================================

class BrainClient:
    def __init__(self, email: str, password: str, base_url: str = BRAIN_API_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (email, password)
        self._authenticate()
    def _authenticate(self) -> None:
        url = self.base_url + "/authentication"
        resp = self.session.post(url)
        if resp.status_code == 401:
            raise RuntimeError(f"BRAIN 登录失败（401）：{resp.text[:200]}")
        if resp.status_code >= 300:
            raise RuntimeError(f"BRAIN 登录异常：HTTP {resp.status_code} {resp.text[:200]}")
        log.info("BRAIN 登录成功")
    def _get(self, path: str, params: dict | None = None) -> dict:
        url = self.base_url + path if path.startswith("/") else urljoin(self.base_url + "/", path)
        resp = self.session.get(url, params=params, timeout=120)
        if resp.status_code >= 300:
            raise RuntimeError(f"GET {url} 失败：HTTP {resp.status_code} {resp.text[:200]}")
        return resp.json()
    def get_datasets(self, instrument_type: str, region: str, delay: int, universe: str) -> pd.DataFrame:
        params = {
            "instrumentType": instrument_type,
            "region": region,
            "delay": delay,
            "universe": universe,
        }
        data = self._get("/data-sets", params=params)
        df = pd.DataFrame(data.get("results", []))
        return _expand_dict_columns(df)
    def get_datafields(
        self,
        instrument_type: str,
        region: str,
        delay: int,
        universe: str,
        dataset_id: str,
        data_type: str = "MATRIX",
    ) -> pd.DataFrame:
        collected: list[dict] = []
        offset = 0
        limit = 50
        # 先请求 count
        first = self._get(
            "/data-fields",
            params={
                "instrumentType": instrument_type,
                "region": region,
                "delay": delay,
                "universe": universe,
                "type": data_type if data_type != "ALL" else None,
                "dataset.id": dataset_id,
                "limit": limit,
                "offset": 0,
            },
        )
        count = first.get("count", 0)
        if count == 0 and data_type != "ALL":
            log.warning(f"type={data_type} 无字段，回退 type=ALL 重试")
            return self.get_datafields(instrument_type, region, delay, universe, dataset_id, data_type="ALL")
        if count == 0:
            return pd.DataFrame()
        collected.extend(first.get("results", []))
        offset = limit
        while offset < count:
            page = self._get(
                "/data-fields",
                params={
                    "instrumentType": instrument_type,
                    "region": region,
                    "delay": delay,
                    "universe": universe,
                    "type": data_type if data_type != "ALL" else None,
                    "dataset.id": dataset_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            collected.extend(page.get("results", []))
            offset += limit
        df = pd.DataFrame(collected)
        return _expand_dict_columns(df)
    def get_operators(self) -> pd.DataFrame:
        data = self._get("/operators")
        df = pd.DataFrame(data)
        if "scope" in df.columns:
            df = df.explode("scope").reset_index(drop=True)
        return df
def _expand_dict_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    for col in list(df.columns):
        sample = next((v for v in df[col] if isinstance(v, dict)), None)
        if sample is None:
            continue
        for k in sample.keys():
            new_col = f"{col}_{k}" if col != k else k
            df[new_col] = df[col].apply(lambda v: v.get(k) if isinstance(v, dict) else None)
    return df
# =============================================================================
# 论文预搜索：arXiv + Semantic Scholar 两级
# =============================================================================
_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "after", "before",
    "field", "data", "dataset", "value", "values", "using", "used", "between", "under",
    "change", "changes", "amount", "price", "market", "transaction", "transactions",
    "security", "recorded", "reported", "level", "total", "number", "event", "events",
    "company", "companies", "stock", "shares", "share", "ownership", "insider", "holding",
}
_CATEGORY_BASE_TERMS = {
    "insiders": ["insider trading", "director dealing", "ownership disclosure", "informed trading"],
    "analyst": ["analyst revision", "earnings forecast", "recommendation change"],
    "news": ["news sentiment", "media attention", "information diffusion"],
    "fundamental": ["fundamental anomaly", "accounting signal", "valuation ratio"],
    "model": ["factor model", "return prediction", "cross sectional alpha"],
    "risk": ["risk premium", "volatility forecasting", "systematic risk"],
    "macro": ["macro surprise", "economic cycle", "asset pricing"],
    "institutions": ["institutional ownership", "fund flow", "investor attention"],
}
def _tokenize_terms(text: str) -> list[str]:
    raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_\-/]{2,}", str(text or "").lower())
    terms: list[str] = []
    for term in raw_terms:
        normalized = term.replace("_", " ").replace("/", " ").replace("-", " ").strip()
        if not normalized or normalized in _STOPWORDS or len(normalized) < 4:
            continue
        if normalized not in terms:
            terms.append(normalized)
    return terms
def build_academic_queries(
    dataset_id: str,
    dataset_name: str | None,
    dataset_description: str | None,
    fields_summary: list[dict],
    max_queries: int = PAPER_MAX_QUERIES,
) -> list[str]:
    category_terms: list[str] = []
    low_id = (dataset_id or "").lower()
    for prefix, terms in _CATEGORY_BASE_TERMS.items():
        if low_id.startswith(prefix):
            category_terms = terms
            break
    blobs: list[str] = [dataset_name or "", dataset_description or ""]
    for item in fields_summary[: min(len(fields_summary), 12)]:
        blobs.append(str(item.get("description") or ""))
        blobs.append(str(item.get("id") or ""))
    extracted: list[str] = []
    for blob in blobs:
        for term in _tokenize_terms(blob):
            if term not in extracted:
                extracted.append(term)
    queries: list[str] = []
    for term in (category_terms + extracted):
        if term not in queries:
            queries.append(term)
    if not queries:
        queries = [dataset_id.replace("_", " ")]
    return queries[:max_queries]
def _arxiv_fetch_entries(query: str, per_query: int, timeout_s: int) -> list[ET.Element]:
    url = (
        "http://export.arxiv.org/api/query?search_query="
        + quote_plus(query)
        + f"&start=0&max_results={per_query}&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        resp = requests.get(url, timeout=timeout_s, headers={"User-Agent": "seed-alpha-generator/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as exc:
        log.warning(f"arXiv 查询失败：{exc}")
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    return root.findall("atom:entry", ns)
def search_arxiv_papers(
    dataset_id: str,
    dataset_name: str | None,
    dataset_description: str | None,
    fields_summary: list[dict],
    max_queries: int = PAPER_MAX_QUERIES,
    per_query: int = PAPER_PER_QUERY,
    year_from: int = PAPER_YEAR_FROM,
    timeout_s: int = PAPER_TIMEOUT_SECONDS,
) -> dict:
    queries = build_academic_queries(dataset_id, dataset_name, dataset_description, fields_summary, max_queries)
    collected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    relevance_terms = [t.lower() for t in queries]
    def _score(title: str, summary: str, q: str) -> int:
        hay = f"{title} {summary}".lower()
        s = 0
        for t in relevance_terms:
            if t and t in hay:
                s += 3
        if q.lower() in hay:
            s += 4
        for t in ("return", "alpha", "asset pricing", "trading", "market", "stock", "equity"):
            if t in hay:
                s += 1
        return s
    min_score = 2
    def _parse(entries: list[ET.Element], q: str) -> None:
        for entry in entries:
            title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
            summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
            published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
            year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
            if year is None or year < year_from:
                continue
            authors = []
            for a in entry.findall("atom:author", ns):
                name = (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
                if name:
                    authors.append(name)
            score = _score(title, summary, q)
            key = (title.lower(), str(year))
            if not title or key in seen or score < min_score:
                continue
            seen.add(key)
            collected.append({
                "title": title, "year": year, "authors": authors[:5],
                "summary": summary[:800], "query": q, "relevance_score": score,
            })
    # 第一轮：精确短语
    for q in queries:
        _parse(_arxiv_fetch_entries(f'all:"{q}"', per_query, timeout_s), q)
    # 第二轮：AND 拆词
    if not collected:
        for q in queries:
            parts = q.split()
            loose = f"all:{q}" if len(parts) <= 1 else " AND ".join(f"all:{w}" for w in parts)
            _parse(_arxiv_fetch_entries(loose, per_query, timeout_s), q)
    # 第三轮：金融通用词回退
    if not collected:
        for fq in [
            "quantitative finance alpha factor",
            "cross-sectional stock return anomaly",
            "fundamental analysis stock prediction",
        ]:
            loose = " AND ".join(f"all:{w}" for w in fq.split())
            _parse(_arxiv_fetch_entries(loose, 3, timeout_s), fq)
    collected.sort(key=lambda it: (it.get("relevance_score") or 0, it.get("year") or 0), reverse=True)
    note = "arXiv（精确+宽松+通用回退三级搜索）" if collected else "arXiv（三级搜索均无结果）"
    return {
        "source": "arXiv",
        "year_from": year_from,
        "query_terms": queries,
        "search_note": f"arXiv submittedDate 倒序搜索，{note}，优先保留 {year_from} 年及之后。",
        "papers": collected[:20],
    }
def search_semantic_scholar(
    dataset_id: str,
    dataset_name: str | None,
    dataset_description: str | None,
    fields_summary: list[dict],
    max_queries: int = 4,
    per_query: int = PAPER_PER_QUERY,
    year_from: int = PAPER_YEAR_FROM,
    timeout_s: int = 20,
) -> dict:
    queries = build_academic_queries(dataset_id, dataset_name, dataset_description, fields_summary, max_queries)
    collected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    terms = [t.lower() for t in queries]
    base = "https://api.semanticscholar.org/graph/v1/paper/search"
    def _score(title: str, abstract: str, q: str) -> int:
        hay = f"{title} {abstract}".lower()
        s = 0
        for t in terms:
            if t and t in hay:
                s += 3
        if q.lower() in hay:
            s += 4
        for t in ("return", "alpha", "asset pricing", "trading", "market", "stock", "equity", "factor", "anomaly"):
            if t in hay:
                s += 1
        return s
    for q in queries:
        params = {
            "query": f"{q} finance stock",
            "limit": per_query,
            "fields": "title,year,authors,abstract",
            "year": f"{year_from}-",
        }
        try:
            resp = requests.get(base, params=params, timeout=timeout_s,
                                headers={"User-Agent": "seed-alpha-generator/1.0"})
            if resp.status_code == 429:
                time.sleep(2)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning(f"Semantic Scholar 查询失败：{exc}")
            continue
        for p in data.get("data") or []:
            title = (p.get("title") or "").strip()
            year = p.get("year")
            abstract = (p.get("abstract") or "").strip()
            if not title or (year is not None and year < year_from):
                continue
            authors = [a.get("name", "").strip() for a in (p.get("authors") or [])[:5] if a.get("name")]
            s_ = _score(title, abstract, q)
            key = (title.lower(), str(year))
            if key in seen or s_ < 1:
                continue
            seen.add(key)
            collected.append({
                "title": title, "year": year, "authors": authors,
                "summary": abstract[:800], "query": q, "relevance_score": s_,
            })
        time.sleep(0.5)
    collected.sort(key=lambda it: (it.get("relevance_score") or 0, it.get("year") or 0), reverse=True)
    return {
        "source": "Semantic Scholar",
        "year_from": year_from,
        "query_terms": queries,
        "search_note": f"Semantic Scholar 候补搜索，保留 {year_from} 年及之后论文。",
        "papers": collected[:20],
    }
def search_academic_papers(
    dataset_id: str,
    dataset_name: str | None,
    dataset_description: str | None,
    fields_summary: list[dict],
) -> dict:
    """统一入口：先 arXiv 三级搜索，失败则 Semantic Scholar 候补。"""
    r = search_arxiv_papers(dataset_id, dataset_name, dataset_description, fields_summary)
    if r.get("papers"):
        return r
    log.info("arXiv 无结果，启用 Semantic Scholar 候补搜索")
    r2 = search_semantic_scholar(dataset_id, dataset_name, dataset_description, fields_summary)
    if r2.get("papers"):
        r2["query_terms"] = list(dict.fromkeys(r.get("query_terms", []) + r2.get("query_terms", [])))
        r2["search_note"] = (
            f"arXiv 无结果，已回退 Semantic Scholar；"
            f"共命中 {len(r2['papers'])} 篇 {r2.get('year_from', PAPER_YEAR_FROM)} 年后论文。"
        )
        return r2
    log.warning("arXiv 与 Semantic Scholar 均无结果，LLM 将仅基于通用金融常识生成 Idea")
    return {
        "source": "none",
        "year_from": PAPER_YEAR_FROM,
        "query_terms": r.get("query_terms", []),
        "search_note": "两大论文源均未命中。请基于金融经济学常识和字段含义生成 Idea，无需引用具体论文。",
        "papers": [],
    }
# =============================================================================
# LLM 调用（OpenAI / Anthropic 双适配 + 流式）
# =============================================================================
def _is_anthropic(api_key: str, base_url: str, model: str) -> bool:
    m = (model or "").lower()
    return (
        m.startswith("claude")
        or "claude-" in m
        or "opus" in m
        or api_key.startswith("sk-ant-")
        or "anthropic" in (base_url or "").lower()
    )
def call_llm(api_key: str, base_url: str, model: str, system_prompt: str, user_prompt: str,
             timeout_s: int = AI_TIMEOUT_SECONDS) -> str:
    base_url = (base_url or "").rstrip("/") or "https://api.moonshot.cn/v1"
    if _is_anthropic(api_key, base_url, model):
        return _anthropic_stream(api_key, base_url, model, system_prompt, user_prompt, timeout_s)
    return _openai_stream(api_key, base_url, model, system_prompt, user_prompt, timeout_s)
def _openai_stream(api_key, base_url, model, system_prompt, user_prompt, timeout_s) -> str:
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
    }
    retries, backoff = 2, 2.0
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s, stream=True)
            resp.encoding = "utf-8"
            if resp.status_code >= 300:
                raise RuntimeError(f"LLM API 错误 {resp.status_code}: {resp.text[:500]}")
            parts: list[str] = []
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                line = raw.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except Exception:
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content")
                if piece:
                    parts.append(str(piece))
                    sys.stdout.write(str(piece))
                    sys.stdout.flush()
                if choices[0].get("finish_reason"):
                    break
            result = "".join(parts)
            if result:
                print()
                return result
            # 流式为空，回退一次非流式
            log.warning("流式返回为空，回退非流式")
            payload_ns = dict(payload, stream=False)
            r2 = requests.post(url, headers=headers, json=payload_ns, timeout=timeout_s)
            if r2.status_code < 300:
                data = r2.json()
                choices = data.get("choices") or []
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            return ""
        except (requests.Timeout, requests.ConnectionError, requests.RequestException) as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            time.sleep(backoff * (2 ** attempt))
    raise last_exc or RuntimeError("LLM 请求失败")
def _anthropic_stream(api_key, base_url, model, system_prompt, user_prompt, timeout_s) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "stream": True,
    }
    retries, backoff = 2, 2.0
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s, stream=True)
            resp.encoding = "utf-8"
            if resp.status_code >= 300:
                raise RuntimeError(f"Anthropic API 错误 {resp.status_code}: {resp.text[:500]}")
            parts: list[str] = []
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                line = raw.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except Exception:
                    continue
                if event.get("type") == "content_block_delta":
                    text = (event.get("delta") or {}).get("text", "")
                    if text:
                        parts.append(text)
                        sys.stdout.write(text)
                        sys.stdout.flush()
                elif event.get("type") == "message_stop":
                    break
            print()
            return "".join(parts)
        except (requests.Timeout, requests.ConnectionError, requests.RequestException) as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            time.sleep(backoff * (2 ** attempt))
    raise last_exc or RuntimeError("Anthropic 请求失败")
# =============================================================================
# Prompt 构建（内嵌两份 SKILL 精华说明）
# =============================================================================
_FEATURE_ENGINEERING_SKILL = """
# Brain Data Feature Engineering
Purpose: transform BRAIN dataset fields into deep, meaningful feature engineering ideas.
Workflow:
1. Deconstruct each field's meaning (what/how/when/why/reliability).
2. Academic Paper Pre-Search: for every feature concept, cite the supplied academic_search_context;
   if no direct match, explicitly state "No direct academic reference found from search" and give economic logic.
3. Reasoning & Analysis: map relationships, generate feature concepts by asking:
   - What is stable? What is changing? What is anomalous? What is correlated? What is noisy?
4. For every concept, produce ONE implementation template that uses suffix-only {variable} placeholders
   drawn from allowed_placeholders.
Output: markdown with the exact English headings shown in OUTPUT_TEMPLATE.
"""
_FEATURE_IMPLEMENTATION_SKILL = """
# Brain Feature Implementation
Convert idea documents into concrete Alpha expressions.
Rules:
- Template MUST be a Python format string using {variable}.
- {variable} MUST be the suffix-only form (no dataset prefix, no horizon), matching real field ids by substring.
- Use ONLY operators from allowed_operators.
- Do not include shell syntax, markdown code fences, or literal field ids wrapped in braces.
"""
def _read_pick_col(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None
def build_field_summary(fields_df: pd.DataFrame) -> tuple[list[dict], int]:
    id_col = _read_pick_col(fields_df, ["id", "field_id", "fieldId"])
    desc_col = _read_pick_col(fields_df, ["description", "desc"])
    rows: list[dict] = []
    for _, row in fields_df.iterrows():
        rows.append({
            "id": row.get(id_col) if id_col else None,
            "description": row.get(desc_col) if desc_col else None,
        })
    return rows, int(fields_df.shape[0])
def build_allowed_suffixes(fields_df: pd.DataFrame, max_suffixes: int = 300) -> list[str]:
    id_col = _read_pick_col(fields_df, ["id", "field_id", "fieldId"])
    if not id_col:
        return []
    field_ids = fields_df[id_col].dropna().astype(str).tolist()
    dataset_code = detect_dataset_code(field_ids)
    counts: dict[str, int] = {}
    for raw in field_ids:
        parts = [p for p in str(raw).split("_") if p]
        if len(parts) < 2:
            continue
        for n in range(1, min(6, len(parts))):
            suffix = "_".join(parts[-n:])
            if suffix.replace("_", "").isdigit():
                continue
            if dataset_code and suffix.lower().startswith(dataset_code.lower() + "_"):
                continue
            if n == 1 and len(suffix) < 8:
                continue
            if len(suffix) < 6:
                continue
            counts[suffix] = counts.get(suffix, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (kv[1], kv[0].count("_"), len(kv[0])), reverse=True)
    out: list[str] = []
    for suffix, _ in ranked:
        if suffix not in out:
            out.append(suffix)
        if len(out) >= max_suffixes:
            break
    return out
def detect_dataset_code(field_ids: list[str]) -> str | None:
    if not field_ids:
        return None
    counts: dict[str, int] = {}
    for fid in field_ids:
        tok = (str(fid).split("_", 1)[0] or "").strip()
        if tok:
            counts[tok] = counts.get(tok, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]
def _vector_ratio(df: pd.DataFrame) -> float:
    dtype_col = _read_pick_col(df, ["type", "dataType", "data_type"])
    if not dtype_col:
        return 0.0
    vals = df[dtype_col].astype(str).value_counts().to_dict()
    vec = vals.get("VECTOR", 0)
    total = sum(vals.values())
    return (vec / total) if total else 0.0
def filter_operators(df: pd.DataFrame, keep_vector: bool) -> list[dict]:
    df = df.copy()
    name_col = _read_pick_col(df, ["name", "operator", "op", "id"])
    scope_col = _read_pick_col(df, ["scope", "scopes"])
    cat_col = _read_pick_col(df, ["category", "group", "type"])
    desc_col = _read_pick_col(df, ["description", "desc", "help", "doc"])
    def_col = _read_pick_col(df, ["definition", "syntax"])
    if scope_col:
        df = df[df[scope_col].astype(str).str.upper() == "REGULAR"]
    if cat_col:
        df = df[df[cat_col].astype(str).str.lower() != "group"]
        if not keep_vector:
            df = df[df[cat_col].astype(str).str.lower() != "vector"]
    if name_col:
        banned = re.compile(r"(?:rank|neutral|normal|scal|zscore)", flags=re.IGNORECASE)
        df = df[~df[name_col].astype(str).str.contains(banned, na=False)]
        df = df.drop_duplicates(subset=[name_col]).reset_index(drop=True)
    out: list[dict] = []
    for _, row in df.iterrows():
        item = {
            "name": row.get(name_col) if name_col else None,
            "category": row.get(cat_col) if cat_col else None,
            "scope": row.get(scope_col) if scope_col else None,
            "description": row.get(desc_col) if desc_col else None,
            "definition": row.get(def_col) if def_col else None,
        }
        out.append({k: v for k, v in item.items() if v is not None})
    return out
def build_prompt(
    dataset_id: str,
    dataset_name: str | None,
    dataset_description: str | None,
    data_category: str,
    region: str,
    delay: int,
    universe: str,
    data_type: str,
    fields_summary: list[dict],
    field_count: int,
    allowed_suffixes: list[str],
    allowed_operators: list[dict],
    academic_context: dict,
) -> tuple[str, str]:
    academic_guidance = {
        "source": academic_context.get("source") or "arXiv",
        "year_from": academic_context.get("year_from"),
        "query_terms": academic_context.get("query_terms") or [],
        "result_count": len(academic_context.get("papers") or []),
        "search_note": academic_context.get("search_note") or "",
        "papers": academic_context.get("papers") or [],
        "usage_rules": [
            "Use the academic_search_context as the primary source for the 'Academic Paper Pre-Search' section.",
            "Prefer recent papers from the supplied results; never fabricate titles, authors, or years.",
            "If no direct match, explicitly say 'No direct academic reference found from search' and give economic logic.",
            "Even when result_count=0, you MUST still generate feature concepts and valid Implementation Examples.",
        ],
    }
    prompt_lines = [
        "You are executing two skills in sequence:",
        "1) brain-data-feature-engineering",
        "2) brain-feature-implementation",
        "The following SKILL specs are authoritative; follow them exactly.",
        "",
        "--- SKILL (brain-data-feature-engineering) ---",
        _FEATURE_ENGINEERING_SKILL.strip(),
        "",
        "--- SKILL (brain-feature-implementation) ---",
        _FEATURE_IMPLEMENTATION_SKILL.strip(),
        "------",
        f'"allowed_operators": {allowed_operators}',
        "-------",
        f'"allowed_placeholders": {allowed_suffixes}',
        "",
    ]
    if str(data_type).upper() == "VECTOR":
        prompt_lines.append(
            "All the following data is vector type; use a vector operator (vec_avg/vec_sum/vec_max/vec_min/"
            "vec_std/vec_count) to aggregate BEFORE any further processing. Vector operators cannot be nested."
        )
        vector_ops = sorted({
            str(op.get("name", "")).strip()
            for op in allowed_operators
            if isinstance(op, dict) and str(op.get("category", "")).lower() == "vector" and op.get("name")
        }) or ["vec_avg", "vec_sum", "vec_max", "vec_min", "vec_std", "vec_count"]
        prompt_lines.append("Available vector operators: " + ", ".join(vector_ops))
    prompt_lines.extend([
        "CRITICAL OUTPUT RULES (so the expression expander can succeed):",
        "- Every Implementation Example MUST be a Python format template using {variable}.",
        "- Every {variable} MUST come from allowed_placeholders (suffix-only, no dataset code/horizon).",
        "- Only operators from allowed_operators are permitted.",
        "- Do NOT wrap raw field ids in braces; use backticks for illustration.",
        "- Include the following metadata verbatim near the top:",
        f"  **Dataset**: {dataset_id}",
        f"  **Region**: {region}",
        f"  **Delay**: {delay}",
        "- Use English section titles; do NOT translate **Concept** or **Implementation Example**.",
        "- For each feature concept, write:",
        "  **Concept**: <English concept name>",
        "  - **Implementation Example**: `subtract({foo}, {bar})`",
    ])
    system_prompt = "\n".join(prompt_lines)
    user_prompt = {
        "instructions": {
            "output_format": "Fill OUTPUT_TEMPLATE with concrete content using the required headings.",
            "implementation_examples": (
                "Each Implementation Example is a template with {variable} placeholders drawn from allowed_placeholders; "
                "suffix-only names, no dataset prefix/horizon."
            ),
            "no_code_fences": True,
            "do_not_invent_placeholders": True,
            "academic_search_requirement": (
                "Use academic_search_context as the basis for Academic Paper Pre-Search and per-concept Academic Basis."
            ),
        },
        "dataset_context": {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "dataset_description": dataset_description,
            "category": data_category,
            "region": region,
            "delay": delay,
            "universe": universe,
            "field_count": field_count,
        },
        "academic_search_context": academic_guidance,
        "fields": fields_summary,
    }
    return system_prompt, json.dumps(user_prompt, ensure_ascii=False, indent=2)
# =============================================================================
# 模板解析 + 占位符标准化 + 展开到表达式
# =============================================================================
def ensure_metadata_block(md: str, dataset_id: str, region: str, delay: int) -> str:
    has_ds = re.search(r"^\*\*Dataset\*\*:\s*\S+", md, flags=re.MULTILINE) is not None
    has_rg = re.search(r"^\*\*Region\*\*:\s*\S+", md, flags=re.MULTILINE) is not None
    has_dl = re.search(r"^\*\*Delay\*\*:\s*\d+", md, flags=re.MULTILINE) is not None
    if has_ds and has_rg and has_dl:
        return md
    block = ["", f"**Dataset**: {dataset_id}", f"**Region**: {region}", f"**Delay**: {delay}", ""]
    lines = md.splitlines()
    insert_at = 0
    for i, line in enumerate(lines[:10]):
        if line.strip():
            insert_at = i + 1
            break
    return "\n".join(lines[:insert_at] + block + lines[insert_at:]).lstrip("\n")
def extract_template_blocks(md: str) -> list[dict]:
    concept_re = re.compile(r"^\*\*Concept\*\*\s*:\s*(.*)\s*$")
    impl_re = re.compile(r"\*\*Implementation Example\*\*\s*:\s*(.*)$", flags=re.IGNORECASE)
    backtick_re = re.compile(r"`([^`]*)`")
    boundary_re = re.compile(r"^(?:-{3,}|#{1,6}\s+.*)\s*$")
    lines = md.splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []
    def flush() -> None:
        nonlocal current
        if current:
            while current and not current[0].strip():
                current.pop(0)
            while current and not current[-1].strip():
                current.pop()
            if current:
                blocks.append(current)
        current = []
    for line in lines:
        if concept_re.match(line.strip()):
            flush()
            current = [line]
            continue
        if current and boundary_re.match(line.strip()):
            flush()
            continue
        if current:
            current.append(line)
    flush()
    out: list[dict] = []
    for b in blocks:
        template: str | None = None
        impl_idx: int | None = None
        for i, raw in enumerate(b):
            m = impl_re.search(raw)
            if not m:
                continue
            impl_idx = i
            tail = (m.group(1) or "").strip()
            bt = backtick_re.search(tail)
            if bt:
                template = bt.group(1).strip()
                break
            if tail and "{" in tail and "}" in tail:
                template = tail.strip().strip("`")
                break
            for j in range(i + 1, min(i + 4, len(b))):
                nxt = b[j].strip()
                if not nxt:
                    continue
                bt2 = backtick_re.search(nxt)
                if bt2:
                    template = bt2.group(1).strip()
                    break
                if "{" in nxt and "}" in nxt:
                    template = nxt.strip().strip("`")
                    break
            break
        if not template or "{" not in template or "}" not in template:
            continue
        idea_lines = [raw for i, raw in enumerate(b) if i != impl_idx]
        out.append({"template": template.strip(), "idea": "\n".join(idea_lines).strip()})
    return out
def _compress_to_suffix(var: str, suffixes: list[str]) -> str | None:
    v = var.lower()
    for s in sorted(suffixes, key=len, reverse=True):
        if v.endswith(s.lower()):
            return s
    return None
def _placeholder_matchable(var: str, field_ids: list[str]) -> bool:
    if len(var) <= 3:
        pat = re.compile(rf"(^|_){re.escape(var)}(_|$)", flags=re.IGNORECASE)
        return any(pat.search(str(fid)) for fid in field_ids)
    return any(var in str(fid) for fid in field_ids)
def normalize_template(template: str, field_ids: list[str], suffixes: list[str], dataset_code: str | None) -> tuple[str, bool]:
    vars_ = re.findall(r"\{([A-Za-z0-9_]+)\}", template)
    if not vars_:
        return template, False
    mapping: dict[str, str] = {}
    for v in set(vars_):
        new_v = v
        if dataset_code and new_v.lower().startswith(dataset_code.lower() + "_"):
            new_v = new_v[len(dataset_code) + 1:]
        comp = _compress_to_suffix(new_v, suffixes)
        if comp:
            new_v = comp
        mapping[v] = new_v
    normalized = template
    for src, dst in mapping.items():
        normalized = normalized.replace("{" + src + "}", "{" + dst + "}")
    vars_after = re.findall(r"\{([A-Za-z0-9_]+)\}", normalized)
    ok = all(_placeholder_matchable(v, field_ids) for v in vars_after)
    return normalized, ok
def _matches_metric(fid: str, metric: str) -> bool:
    fid = str(fid)
    m = str(metric)
    if len(m) <= 3:
        return re.search(rf"(^|_){re.escape(m)}(_|$)", fid, flags=re.IGNORECASE) is not None
    return m in fid
def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i
def expand_template_to_expressions(fields_df: pd.DataFrame, template: str) -> list[str]:
    metrics = re.findall(r"\{([A-Za-z0-9_]+)\}", template)
    if not metrics:
        return []
    metrics = sorted(metrics, key=len, reverse=True)
    primary = metrics[0]
    id_col = _read_pick_col(fields_df, ["id", "field_id", "fieldId"])
    if not id_col:
        return []
    ids = fields_df[id_col].dropna().astype(str).tolist()
    cands_by_metric: dict[str, list[str]] = {}
    for m in metrics:
        seen, uniq = set(), []
        for fid in ids:
            if _matches_metric(fid, m) and fid not in seen:
                seen.add(fid)
                uniq.append(fid)
        cands_by_metric[m] = uniq
    if not cands_by_metric.get(primary):
        return []
    for m in metrics[1:]:
        if not cands_by_metric.get(m):
            return []
    results: list[str] = []
    seen_expr: set[str] = set()
    primary_candidates = cands_by_metric[primary][:MAX_PRIMARY_CANDIDATES]
    for primary_id in primary_candidates:
        chosen: dict[str, list[str]] = {primary: [primary_id]}
        for m in metrics[1:]:
            ranked = sorted(cands_by_metric[m], key=lambda fid: _common_prefix_len(primary_id, fid), reverse=True)
            chosen[m] = ranked[:MAX_SECONDARY_CHOICES]
        pools = [chosen[m] for m in metrics]
        for combo in itertools.product(*pools):
            field_map = dict(zip(metrics, combo))
            try:
                expr = template.format(**field_map)
            except Exception:
                continue
            if expr in seen_expr:
                continue
            seen_expr.add(expr)
            results.append(expr)
            if len(results) >= MAX_EXPRESSIONS_PER_TEMPLATE:
                return results
    return results
# =============================================================================
# 基础表达式健全性检查
# =============================================================================
def sanity_check_expression(expr: str) -> bool:
    """括号平衡、无残留 {placeholder}、非空。"""
    if not expr or not expr.strip():
        return False
    if "{" in expr or "}" in expr:
        return False
    depth = 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
# =============================================================================
# 主流程
# =============================================================================
def infer_data_category(dataset_id: str, fallback: str) -> str:
    if fallback:
        return fallback
    lo = dataset_id.lower()
    for prefix in ["analyst", "fundamental", "earnings", "model", "news",
                   "risk", "macro", "insiders", "institutions", "other"]:
        if lo.startswith(prefix):
            return prefix
    return "general"
def run() -> list[str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("============== Seed Alpha Generator ==============")
    log.info(f"dataset_id={DATASET_ID} region={REGION} delay={DELAY} universe={UNIVERSE} "
             f"instrument_type={INSTRUMENT_TYPE} data_type={DATA_TYPE}")
    data_category = infer_data_category(DATASET_ID, DATA_CATEGORY)
    log.info(f"data_category 推断为: {data_category}")
    # 1. 登录 BRAIN
    client = BrainClient(BRAIN_EMAIL, BRAIN_PASSWORD, BRAIN_API_URL)
    # 2. 数据集元数据
    log.info("拉取数据集元数据...")
    datasets_df = client.get_datasets(INSTRUMENT_TYPE, REGION, DELAY, UNIVERSE)
    dataset_name = dataset_description = None
    id_col = _read_pick_col(datasets_df, ["id", "dataset_id", "datasetId"])
    name_col = _read_pick_col(datasets_df, ["name", "dataset_name", "datasetName"])
    desc_col = _read_pick_col(datasets_df, ["description", "desc", "dataset_description"])
    if id_col:
        match = datasets_df[datasets_df[id_col].astype(str) == str(DATASET_ID)]
        if not match.empty:
            row = match.iloc[0]
            dataset_name = row.get(name_col) if name_col else None
            dataset_description = row.get(desc_col) if desc_col else None
    log.info(f"dataset_name={dataset_name!r} dataset_description 长度={len(str(dataset_description or ''))}")
    # 3. 数据字段
    log.info("拉取数据字段...")
    fields_df = client.get_datafields(INSTRUMENT_TYPE, REGION, DELAY, UNIVERSE, DATASET_ID, DATA_TYPE)
    if fields_df is None or fields_df.empty:
        log.error(f"未获取到字段；请检查 dataset_id/region/delay/universe 是否匹配数据集。")
        return []
    log.info(f"拿到 {len(fields_df)} 个字段")
    fields_summary, field_count = build_field_summary(fields_df)
    allowed_suffixes = build_allowed_suffixes(fields_df, max_suffixes=300)
    log.info(f"生成 {len(allowed_suffixes)} 个 allowed_placeholders")
    # 4. 操作符
    allowed_operators: list[dict] = []
    try:
        log.info("拉取操作符清单...")
        ops_df = client.get_operators()
        keep_vector = str(DATA_TYPE).upper() == "VECTOR" or _vector_ratio(fields_df) > 0.5
        allowed_operators = filter_operators(ops_df, keep_vector=keep_vector)[:MAX_ALLOWED_OPERATORS_IN_PROMPT]
        log.info(f"过滤后保留 {len(allowed_operators)} 个操作符 (keep_vector={keep_vector})")
    except Exception as exc:
        log.warning(f"拉取操作符失败，继续但会降级: {exc}")
    # 5. 论文预搜索
    log.info("执行论文预搜索（arXiv + Semantic Scholar 候补）...")
    academic_context = search_academic_papers(DATASET_ID, dataset_name, dataset_description, fields_summary)
    log.info(f"论文命中 {len(academic_context.get('papers') or [])} 篇 (source={academic_context.get('source')})")
    # 6. 构建 prompt
    system_prompt, user_prompt = build_prompt(
        dataset_id=DATASET_ID,
        dataset_name=dataset_name,
        dataset_description=dataset_description,
        data_category=data_category,
        region=REGION,
        delay=DELAY,
        universe=UNIVERSE,
        data_type=DATA_TYPE,
        fields_summary=fields_summary,
        field_count=field_count,
        allowed_suffixes=allowed_suffixes,
        allowed_operators=allowed_operators,
        academic_context=academic_context,
    )
    # 7. 调用 LLM
    log.info(f"调用 LLM（{AI_MODEL} @ {AI_BASE_URL}）...")
    print("\n---------- LLM 输出开始 ----------")
    report = call_llm(AI_API_KEY, AI_BASE_URL, AI_MODEL, system_prompt, user_prompt, AI_TIMEOUT_SECONDS)
    print("---------- LLM 输出结束 ----------\n")
    if not report:
        log.error("LLM 返回空结果")
        return []
    # 8. 保存 Idea 报告
    ideas_name = f"{REGION}_delay{DELAY}_{DATASET_ID}_ideas.md"
    ideas_path = OUTPUT_DIR / ideas_name
    ideas_path.write_text(ensure_metadata_block(report, DATASET_ID, REGION, DELAY), encoding="utf-8")
    log.info(f"Idea 报告已保存: {ideas_path}")
    # 9. 解析模板
    ideas_text = ideas_path.read_text(encoding="utf-8")
    blocks = extract_template_blocks(ideas_text)
    if not blocks:
        log.error("未在 Idea 报告中找到 **Concept** + **Implementation Example** 模板")
        return []
    id_col2 = _read_pick_col(fields_df, ["id", "field_id", "fieldId"])
    field_ids = fields_df[id_col2].dropna().astype(str).tolist() if id_col2 else []
    dataset_code = detect_dataset_code(field_ids) if field_ids else None
    templates_seen: set[str] = set()
    final_exprs: list[str] = []
    for idx, item in enumerate(blocks, 1):
        tmpl = item.get("template", "")
        if not tmpl:
            continue
        normalized, ok = normalize_template(tmpl, field_ids, allowed_suffixes, dataset_code) if field_ids else (tmpl, True)
        if not ok or normalized in templates_seen:
            log.info(f"[{idx}] 模板跳过: {tmpl!r}")
            continue
        templates_seen.add(normalized)
        log.info(f"[{idx}] 展开模板: {normalized}")
        exprs = expand_template_to_expressions(fields_df, normalized)
        for e in exprs:
            if sanity_check_expression(e):
                final_exprs.append(e)
    final_exprs = list(dict.fromkeys(final_exprs))
    final_path = OUTPUT_DIR / f"{REGION}_delay{DELAY}_{DATASET_ID}_expressions.json"
    final_path.write_text(json.dumps(final_exprs, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"最终生成 {len(final_exprs)} 个表达式，已保存: {final_path}")
    print("\n========== 最终 Alpha 表达式 ==========")
    for i, e in enumerate(final_exprs, 1):
        print(f"{i:4d}. {e}")
    return final_exprs
if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log.warning("用户中断")
        sys.exit(130)
    except Exception as exc:
        log.exception(f"运行失败: {exc}")
        sys.exit(1)
