"""Bean deduplication service using fuzzy matching."""

from typing import List, Tuple
import re

from django.db.models import Q
from fuzzywuzzy import fuzz

from ..models import CoffeeBean


# Thresholds for fuzzy matching
EXACT_MATCH_THRESHOLD = 100
HIGH_SIMILARITY_THRESHOLD = 90
MEDIUM_SIMILARITY_THRESHOLD = 80


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    Args:
        text: Text to normalize

    Returns:
        Normalized lowercase text
    """
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text)
    return text


def find_potential_duplicates(
    *,
    name: str,
    roastery_name: str,
    threshold: int = MEDIUM_SIMILARITY_THRESHOLD
) -> List[Tuple[CoffeeBean, int, str]]:
    """
    Find potential duplicate beans using exact and fuzzy matching.

    Args:
        name: Bean name to check
        roastery_name: Roastery name to check
        threshold: Minimum similarity score (0-100)

    Returns:
        List of (bean, similarity_score, match_type) tuples
        match_type: 'exact', 'fuzzy_name', 'fuzzy_both'
    """
    name_norm = normalize_text(name)
    roastery_norm = normalize_text(roastery_name)

    candidates = []

    # Step 1: Check for exact normalized match
    exact_matches = CoffeeBean.objects.filter(
        name_normalized=name_norm,
        roastery_normalized=roastery_norm,
        is_active=True
    )

    for bean in exact_matches:
        candidates.append((bean, 100, 'exact'))

    # If exact match found, return immediately
    if candidates:
        return candidates

    # Step 2: Fuzzy matching on same roastery
    same_roastery = CoffeeBean.objects.filter(
        roastery_normalized=roastery_norm,
        is_active=True
    ).exclude(name_normalized=name_norm)

    for bean in same_roastery:
        name_similarity = fuzz.ratio(name_norm, bean.name_normalized)
        if name_similarity >= threshold:
            candidates.append((bean, name_similarity, 'fuzzy_name'))

    # Step 3: Fuzzy matching on both name and roastery
    all_beans = CoffeeBean.objects.filter(
        is_active=True
    ).exclude(
        roastery_normalized=roastery_norm
    )[:100]  # Limit for performance

    for bean in all_beans:
        name_similarity = fuzz.ratio(name_norm, bean.name_normalized)
        roastery_similarity = fuzz.ratio(roastery_norm, bean.roastery_normalized)

        # Combined score (weighted average: name 70%, roastery 30%)
        combined_score = int((name_similarity * 0.7) + (roastery_similarity * 0.3))

        if combined_score >= threshold:
            candidates.append((bean, combined_score, 'fuzzy_both'))

    # Sort by similarity score (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    return candidates[:10]  # Return top 10 matches


def batch_find_duplicates(
    *,
    threshold: int = HIGH_SIMILARITY_THRESHOLD
) -> List[dict]:
    """
    Scan entire database for potential duplicates.
    Used for admin cleanup tasks.

    Args:
        threshold: Minimum similarity score

    Returns:
        List of duplicate groups:
        [
            {
                'beans': [bean1, bean2],
                'similarity': int,
                'suggested_merge': (source_id, target_id)
            }
        ]
    """
    all_beans = CoffeeBean.objects.filter(is_active=True)

    # Group by normalized roastery first (performance optimization)
    from collections import defaultdict
    by_roastery = defaultdict(list)

    for bean in all_beans:
        by_roastery[bean.roastery_normalized].append(bean)

    duplicate_groups = []

    for roastery, beans in by_roastery.items():
        if len(beans) < 2:
            continue

        # Check each pair within same roastery
        checked = set()
        for i, bean1 in enumerate(beans):
            for bean2 in beans[i+1:]:
                pair_key = tuple(sorted([bean1.id, bean2.id]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                similarity = fuzz.ratio(
                    bean1.name_normalized,
                    bean2.name_normalized
                )

                if similarity >= threshold:
                    # Suggest merging into bean with more reviews
                    if bean1.review_count >= bean2.review_count:
                        suggested = (bean2.id, bean1.id)  # (source, target)
                    else:
                        suggested = (bean1.id, bean2.id)

                    duplicate_groups.append({
                        'beans': [bean1, bean2],
                        'similarity': similarity,
                        'suggested_merge': suggested
                    })

    # Sort by similarity (highest first)
    duplicate_groups.sort(key=lambda x: x['similarity'], reverse=True)

    return duplicate_groups
