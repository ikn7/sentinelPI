"""
Statistics component for the SentinelPi dashboard.

Provides charts and metrics for monitoring.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st

from src.utils.dates import now


def render_metrics_row(
    items_count: int = 0,
    alerts_count: int = 0,
    sources_count: int = 0,
    unread_count: int = 0,
    items_delta: int | None = None,
    alerts_delta: int | None = None,
) -> None:
    """
    Render a row of key metrics.

    Args:
        items_count: Total items collected.
        alerts_count: Total alerts triggered.
        sources_count: Active sources.
        unread_count: Unread items.
        items_delta: Change in items from previous period.
        alerts_delta: Change in alerts from previous period.
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "📰 Items collectés",
            f"{items_count:,}",
            delta=f"+{items_delta}" if items_delta and items_delta > 0 else items_delta,
            help="Total des items collectés sur la période",
        )

    with col2:
        st.metric(
            "🔔 Alertes",
            alerts_count,
            delta=alerts_delta,
            help="Alertes déclenchées sur la période",
        )

    with col3:
        st.metric(
            "📡 Sources actives",
            sources_count,
            help="Nombre de sources actives",
        )

    with col4:
        st.metric(
            "📭 Non lus",
            unread_count,
            help="Items en attente de lecture",
        )


def render_items_by_day_chart(
    data: list[dict[str, Any]] | None = None,
    days: int = 7,
) -> None:
    """
    Render items collected per day chart.

    Args:
        data: List of {date, count} dicts.
        days: Number of days to show.
    """
    st.subheader("📈 Items par jour")

    if not data:
        # Generate sample data for demo
        sample_data = []
        for i in range(days, 0, -1):
            date = now() - timedelta(days=i)
            sample_data.append({
                "date": date.strftime("%d/%m"),
                "count": 0,
            })
        data = sample_data

    # Prepare for chart
    chart_data = {d["date"]: d["count"] for d in data}

    if all(v == 0 for v in chart_data.values()):
        st.info("📊 Données disponibles après la première collecte.", icon="ℹ️")
    else:
        st.bar_chart(chart_data)


def render_items_by_source_chart(
    data: list[dict[str, Any]] | None = None,
) -> None:
    """
    Render items distribution by source.

    Args:
        data: List of {source, count} dicts.
    """
    st.subheader("📊 Répartition par source")

    if not data:
        st.info("📊 Données disponibles après la première collecte.", icon="ℹ️")
        return

    # Prepare for chart (top 10)
    sorted_data = sorted(data, key=lambda x: x["count"], reverse=True)[:10]
    chart_data = {d["source"]: d["count"] for d in sorted_data}

    st.bar_chart(chart_data)


def render_items_by_category_chart(
    data: list[dict[str, Any]] | None = None,
) -> None:
    """
    Render items distribution by category.

    Args:
        data: List of {category, count} dicts.
    """
    st.subheader("🏷️ Répartition par catégorie")

    if not data:
        st.info("📊 Données disponibles après la première collecte.", icon="ℹ️")
        return

    chart_data = {d["category"]: d["count"] for d in data}
    st.bar_chart(chart_data)


def render_alerts_by_severity_chart(
    data: dict[str, int] | None = None,
) -> None:
    """
    Render alerts distribution by severity.

    Args:
        data: Dict mapping severity to count.
    """
    st.subheader("🔔 Alertes par sévérité")

    if not data:
        data = {
            "🚨 Critical": 0,
            "⚠️ Warning": 0,
            "📢 Notice": 0,
            "ℹ️ Info": 0,
        }

    if all(v == 0 for v in data.values()):
        st.info("📊 Aucune alerte enregistrée.", icon="ℹ️")
    else:
        st.bar_chart(data)


def render_top_keywords(
    keywords: list[tuple[str, int]] | None = None,
    max_keywords: int = 20,
) -> None:
    """
    Render top keywords word cloud or list.

    Args:
        keywords: List of (keyword, count) tuples.
        max_keywords: Maximum keywords to show.
    """
    st.subheader("🔤 Mots-clés fréquents")

    if not keywords:
        st.info("📊 Données disponibles après la première collecte.", icon="ℹ️")
        return

    # Display as tags
    keywords = keywords[:max_keywords]

    # Create tag-like display
    tags_html = ""
    for word, count in keywords:
        size = min(24, 12 + count // 10)
        tags_html += (
            f'<span style="display: inline-block; margin: 3px; padding: 4px 10px; '
            f'background-color: #e0e0e0; border-radius: 15px; font-size: {size}px;">'
            f'{word} <small>({count})</small></span>'
        )

    st.markdown(tags_html, unsafe_allow_html=True)


def render_top_items(
    items: list[dict[str, Any]] | None = None,
    max_items: int = 10,
) -> None:
    """
    Render top items by relevance score.

    Args:
        items: List of item dicts with score.
        max_items: Maximum items to show.
    """
    st.subheader("🏆 Top items (par score)")

    if not items:
        st.info("📊 Données disponibles après la première collecte.", icon="ℹ️")
        return

    items = items[:max_items]

    for i, item in enumerate(items, 1):
        col1, col2, col3 = st.columns([0.5, 5, 1])

        with col1:
            st.markdown(f"**{i}.**")

        with col2:
            title = item.get("title", "Sans titre")
            url = item.get("url")
            source = item.get("source_name", "")

            if url:
                st.markdown(f"[{title}]({url})")
            else:
                st.text(title)

            st.caption(f"📰 {source}")

        with col3:
            score = item.get("relevance_score", 0)
            st.metric("Score", f"{score:.0f}", label_visibility="collapsed")


def render_collection_stats(
    total_collected: int = 0,
    total_new: int = 0,
    total_duplicates: int = 0,
    total_excluded: int = 0,
    collection_time_ms: float = 0,
) -> None:
    """
    Render collection statistics.

    Args:
        total_collected: Total items collected.
        total_new: New items (not duplicates).
        total_duplicates: Duplicates filtered.
        total_excluded: Items excluded by filters.
        collection_time_ms: Collection time in milliseconds.
    """
    st.subheader("📥 Dernière collecte")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Collectés", total_collected)

    with col2:
        st.metric("Nouveaux", total_new)

    with col3:
        st.metric("Doublons", total_duplicates)

    with col4:
        st.metric("Exclus", total_excluded)

    with col5:
        st.metric("Durée", f"{collection_time_ms/1000:.1f}s")


def render_system_stats(
    db_size_mb: float = 0,
    cache_size_mb: float = 0,
    uptime_hours: float = 0,
    memory_usage_mb: float = 0,
) -> None:
    """
    Render system statistics.

    Args:
        db_size_mb: Database size in MB.
        cache_size_mb: Cache size in MB.
        uptime_hours: System uptime in hours.
        memory_usage_mb: Memory usage in MB.
    """
    st.subheader("🖥️ Système")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Base de données", f"{db_size_mb:.1f} MB")

    with col2:
        st.metric("Cache", f"{cache_size_mb:.1f} MB")

    with col3:
        if uptime_hours > 24:
            uptime_str = f"{uptime_hours/24:.1f} jours"
        else:
            uptime_str = f"{uptime_hours:.1f}h"
        st.metric("Uptime", uptime_str)

    with col4:
        st.metric("Mémoire", f"{memory_usage_mb:.0f} MB")


def render_health_indicators(
    sources_healthy: int = 0,
    sources_error: int = 0,
    last_collection: datetime | None = None,
    alerts_pending: int = 0,
) -> None:
    """
    Render system health indicators.

    Args:
        sources_healthy: Number of healthy sources.
        sources_error: Number of sources with errors.
        last_collection: Last collection timestamp.
        alerts_pending: Number of pending alerts.
    """
    st.subheader("🏥 Santé du système")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if sources_error == 0:
            st.success(f"✅ {sources_healthy} sources OK")
        else:
            st.warning(f"⚠️ {sources_error} sources en erreur")

    with col2:
        if last_collection:
            from src.utils.dates import format_relative
            st.info(f"🕐 Dernière collecte: {format_relative(last_collection)}")
        else:
            st.info("🕐 Aucune collecte")

    with col3:
        if alerts_pending > 0:
            st.warning(f"🔔 {alerts_pending} alertes en attente")
        else:
            st.success("🔔 Aucune alerte en attente")

    with col4:
        st.success("🟢 Système opérationnel")
