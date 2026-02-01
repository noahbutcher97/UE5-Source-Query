"""
Advanced Fuzzy Matching algorithms for UE5 entities.
Implements Levenshtein, Jaro-Winkler, and N-Gram similarity metrics.
"""
from typing import List, Set

class FuzzyMatcher:
    """
    Provides advanced string matching algorithms optimized for UE5 naming conventions.
    """

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        Counts insertions, deletions, and substitutions.
        """
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def jaro_winkler_similarity(s1: str, s2: str) -> float:
        """
        Calculate Jaro-Winkler similarity (0.0 to 1.0).
        Better for short strings and prefix matching.
        """
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        match_distance = (max(len1, len2) // 2) - 1
        
        matches = 0
        s1_matches = [False] * len1
        s2_matches = [False] * len2

        # Count matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)
            
            for j in range(start, end):
                if s2_matches[j]:
                    continue
                if s1[i] == s2[j]:
                    s1_matches[i] = True
                    s2_matches[j] = True
                    matches += 1
                    break

        if matches == 0:
            return 0.0

        # Count transpositions
        k = 0
        transpositions = 0
        for i in range(len1):
            if s1_matches[i]:
                while not s2_matches[k]:
                    k += 1
                if s1[i] != s2[k]:
                    transpositions += 1
                k += 1
        
        transpositions //= 2

        # Jaro similarity
        jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0

        # Winkler modification (prefix boost)
        # Standard prefix weight is 0.1, max prefix length is 4
        prefix_len = 0
        for i in range(min(len1, len2, 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break
        
        return jaro + (prefix_len * 0.1 * (1.0 - jaro))

    @staticmethod
    def ngram_similarity(s1: str, s2: str, n: int = 2) -> float:
        """
        Calculate N-Gram similarity (Dice coefficient).
        Good for partial matching and resilience to misspellings.
        """
        if len(s1) < n or len(s2) < n:
            return 0.0
        
        s1_grams = {s1[i:i+n] for i in range(len(s1) - n + 1)}
        s2_grams = {s2[i:i+n] for i in range(len(s2) - n + 1)}
        
        intersection = len(s1_grams.intersection(s2_grams))
        total = len(s1_grams) + len(s2_grams)
        
        return (2.0 * intersection) / total if total > 0 else 0.0

    @staticmethod
    def calculate_compound_score(query: str, candidate: str) -> float:
        """
        Calculate a weighted score combining multiple metrics.
        Returns 0.0 to 1.0.
        """
        query_lower = query.lower()
        candidate_lower = candidate.lower()
        
        # Exact match
        if query == candidate: return 1.0
        if query_lower == candidate_lower: return 0.95
        
        # Jaro-Winkler (Good for typos/prefixes) - Weight: 0.4
        jw = FuzzyMatcher.jaro_winkler_similarity(query_lower, candidate_lower)
        
        # Levenshtein (Normalized) - Weight: 0.3
        dist = FuzzyMatcher.levenshtein_distance(query_lower, candidate_lower)
        max_len = max(len(query), len(candidate))
        lev_sim = 1.0 - (dist / max_len) if max_len > 0 else 0.0
        
        # Bigram (Good for partials) - Weight: 0.3
        # Use bigrams (n=2) for robust partial matching
        ngram = FuzzyMatcher.ngram_similarity(query_lower, candidate_lower, n=2)
        
        # Weighted combination
        # Prioritize Jaro-Winkler for its prefix handling which is common in code search (e.g. typing start of name)
        score = (jw * 0.45) + (lev_sim * 0.3) + (ngram * 0.25)
        
        # Boost for containment (partial match)
        if query_lower in candidate_lower:
            ratio = len(query_lower) / len(candidate_lower)
            # Add up to 0.1 boost based on how much of the string it covers
            score = min(1.0, score + (0.1 * ratio))
            
        return score
