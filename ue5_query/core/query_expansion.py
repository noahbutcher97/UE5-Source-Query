"""
Query Expansion for UE5 terms.
Expands user queries with synonyms, related terms, and semantic variations.
"""
from typing import List, Dict, Set

class QueryExpander:
    """
    Expands queries using a dictionary of UE5-specific synonyms and terms.
    """
    
    # Common abbreviations and synonyms in UE5 development
    SYNONYMS = {
        # Core Types
        "vec": ["FVector", "vector"],
        "vector": ["FVector"],
        "rot": ["FRotator", "rotator"],
        "rotator": ["FRotator"],
        "quat": ["FQuat", "quaternion"],
        "transform": ["FTransform"],
        "string": ["FString", "FName", "FText"],
        "array": ["TArray"],
        "map": ["TMap"],
        "set": ["TSet"],
        
        # Actors/Objects
        "actor": ["AActor"],
        "pawn": ["APawn"],
        "char": ["ACharacter", "character"],
        "character": ["ACharacter"],
        "controller": ["AController", "APlayerController", "AAIController"],
        "hud": ["AHUD"],
        "mode": ["AGameMode", "AGameModeBase"],
        "state": ["AGameState", "AGameStateBase"],
        "instance": ["UGameInstance"],
        
        # Components
        "comp": ["UActorComponent", "USceneComponent"],
        "mesh": ["UStaticMeshComponent", "USkeletalMeshComponent"],
        "capsule": ["UCapsuleComponent"],
        "movement": ["UCharacterMovementComponent", "UPawnMovementComponent"],
        
        # Rendering
        "rhi": ["FRHICommandList", "FRHIResource", "FRHITexture"],
        "shader": ["FGlobalShader", "FShader"],
        "material": ["UMaterial", "UMaterialInstance", "FMaterialProxy"],
        "texture": ["UTexture", "UTexture2D", "FTextureResource"],
        "render": ["FRenderTarget", "UCanvas"],
        
        # AI
        "bt": ["UBehaviorTree", "UBehaviorTreeComponent"],
        "behavior": ["UBehaviorTree", "UBlackboardComponent"],
        "blackboard": ["UBlackboardComponent", "UBlackboardData"],
        "nav": ["UNavigationSystemV1", "ANavigationData"],
        "perception": ["UAIPerceptionComponent", "UAISense"],

        # Networking
        "net": ["UNetDriver", "UNetConnection"],
        "rep": ["Replicated", "GetLifetimeReplicatedProps", "DOREPLIFETIME"],
        "rpc": ["Server", "Client", "NetMulticast"],
        "repl": ["DOREPLIFETIME", "DOREPLIFETIME_CONDITION"],

        # Audio
        "audio": ["UAudioComponent", "USoundCue", "USoundWave"],
        "sound": ["USoundBase", "FAudioDevice"],

        # Animation
        "anim": ["UAnimInstance", "UAnimSequence", "FAnimNode_Base"],
        "montage": ["UAnimMontage"],
        "skeleton": ["USkeleton", "FReferenceSkeleton"],
        
        # Physics/Collision
        "hit": ["FHitResult"],
        "trace": ["LineTraceSingle", "SphereTraceSingle", "CapsuleTraceSingle"],
        "overlap": ["OverlapResult", "FOverlapResult"],
        "collision": ["ECollisionChannel", "ECollisionResponse"],
        "constraint": ["FConstraintInstance", "UPhysicsConstraintComponent", "FConstraintSettings"],
        "constraints": ["FConstraintInstance", "UPhysicsConstraintComponent", "FConstraintSettings"],
        "physics": ["FBodyInstance", "UPhysicsAsset", "FConstraintInstance"],
        "physical": ["FConstraintInstance", "FPhysicalAnimationProfile", "UPhysicalAnimationComponent"],
        "contact": ["FHitResult", "FContactPoint"],
        
        # Files/Modules
        "file": ["header", "source"],
        "location": ["path", "directory"],
        
        # Concepts
        "rep": ["Replicated", "GetLifetimeReplicatedProps", "DOREPLIFETIME"],
        "rpc": ["Server", "Client", "NetMulticast"],
        "log": ["UE_LOG"],
        "print": ["AddOnScreenDebugMessage"],
    }

    @staticmethod
    def expand(query: str) -> List[str]:
        """
        Expand a query string into a list of related search terms.
        
        Args:
            query: The original user query.
            
        Returns:
            List of expanded terms, including the original.
        """
        terms = query.lower().split()
        expanded_set: Set[str] = set()
        expanded_set.add(query) # Always include original
        
        # 1. Direct synonym replacement for whole query
        if query.lower() in QueryExpander.SYNONYMS:
            for syn in QueryExpander.SYNONYMS[query.lower()]:
                expanded_set.add(syn)
                
        # 2. Token-based expansion
        for term in terms:
            if term in QueryExpander.SYNONYMS:
                for syn in QueryExpander.SYNONYMS[term]:
                    # Create a new query variation by replacing the term
                    # This is a simple approach; complex queries might need more sophisticated combination
                    new_query = query.lower().replace(term, syn)
                    expanded_set.add(new_query)
                    # Also add the synonym itself as a standalone search term
                    expanded_set.add(syn)
        
        return list(expanded_set)

    @staticmethod
    def get_related_entities(term: str) -> List[str]:
        """Get just the entity names related to a term"""
        term_lower = term.lower()
        if term_lower in QueryExpander.SYNONYMS:
            return QueryExpander.SYNONYMS[term_lower]
        return []
