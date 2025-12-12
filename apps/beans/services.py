from django.db import transaction
from django.db.models import Q
from fuzzywuzzy import fuzz
from .models import CoffeeBean, CoffeeBeanVariant, MergeHistory
from apps.reviews.models import Review
from apps.purchases.models import PurchaseRecord


class CoffeeBeanDeduplicationService:
    """Service for detecting and merging duplicate coffee beans."""
    
    # Thresholds for fuzzy matching
    EXACT_MATCH_THRESHOLD = 100
    HIGH_SIMILARITY_THRESHOLD = 90
    MEDIUM_SIMILARITY_THRESHOLD = 80
    
    @staticmethod
    def normalize_text(text):
        """Normalize text for comparison."""
        import re
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s-]', '', text)
        return text
    
    @staticmethod
    def find_potential_duplicates(name, roastery_name, threshold=MEDIUM_SIMILARITY_THRESHOLD):
        """
        Find potential duplicate beans using exact and fuzzy matching.
        
        Returns:
            List of (bean, similarity_score, match_type) tuples
        """
        name_norm = CoffeeBeanDeduplicationService.normalize_text(name)
        roastery_norm = CoffeeBeanDeduplicationService.normalize_text(roastery_name)
        
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
            
            # Combined score (weighted average)
            combined_score = (name_similarity * 0.7) + (roastery_similarity * 0.3)
            
            if combined_score >= threshold:
                candidates.append((bean, int(combined_score), 'fuzzy_both'))
        
        # Sort by similarity score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[:10]  # Return top 10 matches
    
    @staticmethod
    def create_bean_with_dedup_check(data, created_by, auto_merge=False):
        """
        Create a new coffee bean with automatic duplicate detection.
        
        Args:
            data: Dict with bean fields (name, roastery_name, etc.)
            created_by: User creating the bean
            auto_merge: If True and exact match exists, return existing bean
        
        Returns:
            (bean, duplicates, was_merged)
            - bean: CoffeeBean instance
            - duplicates: List of potential duplicates
            - was_merged: Boolean indicating if auto-merged
        """
        name = data['name']
        roastery_name = data['roastery_name']
        
        # Find duplicates
        duplicates = CoffeeBeanDeduplicationService.find_potential_duplicates(
            name,
            roastery_name,
            threshold=CoffeeBeanDeduplicationService.HIGH_SIMILARITY_THRESHOLD
        )
        
        # Auto-merge on exact match
        if auto_merge and duplicates:
            exact_match = next(
                (bean for bean, score, match_type in duplicates if match_type == 'exact'),
                None
            )
            if exact_match:
                return exact_match, duplicates, True
        
        # Create new bean
        bean = CoffeeBean.objects.create(
            name=name,
            roastery_name=roastery_name,
            origin_country=data.get('origin_country', ''),
            region=data.get('region', ''),
            processing=data.get('processing', 'washed'),
            roast_profile=data.get('roast_profile', 'medium'),
            roast_date=data.get('roast_date'),
            brew_method=data.get('brew_method', 'filter'),
            description=data.get('description', ''),
            tasting_notes=data.get('tasting_notes', ''),
            created_by=created_by
        )
        
        return bean, duplicates, False
    
    @staticmethod
    @transaction.atomic
    def merge_beans(source_bean_id, target_bean_id, merged_by_user, reason=''):
        """
        Merge source bean into target bean.
        
        Process:
        1. Move all variants from source to target
        2. Update all reviews to point to target
        3. Update all purchases to point to target
        4. Update all library entries
        5. Recalculate target's aggregate rating
        6. Create merge history record
        7. Delete source bean
        
        Args:
            source_bean_id: Bean to be merged (will be deleted)
            target_bean_id: Bean to merge into (will be kept)
            merged_by_user: User performing the merge
            reason: Optional reason for merge
        
        Returns:
            target_bean with updated data
        """
        source = CoffeeBean.objects.select_for_update().get(id=source_bean_id)
        target = CoffeeBean.objects.select_for_update().get(id=target_bean_id)
        
        if source.id == target.id:
            raise ValueError("Cannot merge bean with itself")
        
        # Step 1: Move variants
        CoffeeBeanVariant.objects.filter(coffeebean=source).update(
            coffeebean=target
        )
        
        # Step 2: Update reviews
        Review.objects.filter(coffeebean=source).update(
            coffeebean=target
        )
        
        # Step 3: Update purchases
        PurchaseRecord.objects.filter(coffeebean=source).update(
            coffeebean=target
        )
        
        # Step 4: Update library entries
        from apps.reviews.models import UserLibraryEntry
        from apps.groups.models import GroupLibraryEntry
        
        # User libraries - handle duplicates
        user_libs = UserLibraryEntry.objects.filter(coffeebean=source)
        for lib in user_libs:
            # Check if user already has target in library
            target_lib = UserLibraryEntry.objects.filter(
                user=lib.user,
                coffeebean=target
            ).first()
            
            if target_lib:
                # Keep the older entry, delete duplicate
                lib.delete()
            else:
                # Move to target
                lib.coffeebean = target
                lib.save()
        
        # Group libraries - handle duplicates
        group_libs = GroupLibraryEntry.objects.filter(coffeebean=source)
        for lib in group_libs:
            target_lib = GroupLibraryEntry.objects.filter(
                group=lib.group,
                coffeebean=target
            ).first()
            
            if target_lib:
                # Merge notes if any
                if lib.notes and not target_lib.notes:
                    target_lib.notes = lib.notes
                    target_lib.save()
                lib.delete()
            else:
                lib.coffeebean = target
                lib.save()
        
        # Step 5: Recalculate aggregate rating
        target.update_aggregate_rating()
        
        # Step 6: Create merge history
        MergeHistory.objects.create(
            merged_from=source.id,
            merged_into=target,
            merged_by=merged_by_user,
            reason=reason
        )
        
        # Step 7: Soft delete source (mark inactive instead of hard delete)
        source.is_active = False
        source.name = f"[MERGED] {source.name}"
        source.save()
        
        return target
    
    @staticmethod
    def batch_find_duplicates(threshold=HIGH_SIMILARITY_THRESHOLD):
        """
        Scan entire database for potential duplicates.
        Used for admin cleanup tasks.
        
        Returns:
            List of duplicate groups: [
                {
                    'beans': [bean1, bean2, ...],
                    'max_similarity': int,
                    'suggested_merge': (source_id, target_id)
                }
            ]
        """
        all_beans = CoffeeBean.objects.filter(is_active=True)
        
        # Group by normalized roastery first (faster)
        from collections import defaultdict
        by_roastery = defaultdict(list)
        
        for bean in all_beans:
            by_roastery[bean.roastery_normalized].append(bean)
        
        duplicate_groups = []
        
        for roastery, beans in by_roastery.items():
            if len(beans) < 2:
                continue
            
            # Check each pair
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
                            suggested = (bean2.id, bean1.id)
                        else:
                            suggested = (bean1.id, bean2.id)
                        
                        duplicate_groups.append({
                            'beans': [bean1, bean2],
                            'max_similarity': similarity,
                            'suggested_merge': suggested
                        })
        
        # Sort by similarity (highest first)
        duplicate_groups.sort(key=lambda x: x['max_similarity'], reverse=True)
        
        return duplicate_groups