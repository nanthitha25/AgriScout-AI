import os
import json
import numpy as np
from typing import List, Dict, Any
from google import genai

EMBEDDINGS_FILE = "startup_embeddings.json"


def get_similarity_cache() -> Dict[str, List[float]]:
    """
    Retrieve stored embeddings cache. Key is startup name, value is embedding float list.
    """
    if os.path.exists(EMBEDDINGS_FILE):
        try:
            with open(EMBEDDINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading embeddings cache: {e}")
            return {}
    return {}


def save_similarity_cache(cache: Dict[str, List[float]]) -> None:
    """
    Save updated embeddings to cache file.
    """
    try:
        with open(EMBEDDINGS_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Error saving embeddings cache: {e}")


def get_embedding(client: genai.Client, text: str) -> List[float]:
    """
    Fetch a 768-dimension text embedding vector using Gemini Client.
    """
    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        # Verify response structure
        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
            
        print("Embed response empty. Falling back to dummy vector.")
        return [0.0] * 768
    except Exception as e:
        print(f"Failed to generate embedding: {e}")
        # Return a zero vector of dimension 768 as fallback
        return [0.0] * 768


def get_similar_startups(client: genai.Client, target_name: str, all_startups: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Compute cosine similarity between the target startup's description and all other startups.
    Caches embeddings to minimize Gemini API calls.
    """
    cache = get_similarity_cache()
    
    # Locate target startup
    target_startup = next((s for s in all_startups if s["startup_name"].lower() == target_name.lower()), None)
    if not target_startup:
        print(f"Target startup '{target_name}' not found in database.")
        return []
        
    target_desc = target_startup["brief_description"]
    target_actual_name = target_startup["startup_name"]
    
    # 1. Ensure target embedding is cached
    if target_actual_name not in cache:
        cache[target_actual_name] = get_embedding(client, target_desc)
        save_similarity_cache(cache)
        
    target_vector = np.array(cache[target_actual_name])
    
    similarities = []
    
    # 2. Iterate and compare with other startups
    for startup in all_startups:
        name = startup["startup_name"]
        if name.lower() == target_actual_name.lower():
            continue
            
        desc = startup["brief_description"]
        if not desc:
            continue
            
        # Ensure other startup embedding is cached
        if name not in cache:
            cache[name] = get_embedding(client, desc)
            save_similarity_cache(cache)
            
        other_vector = np.array(cache[name])
        
        # Calculate Cosine Similarity: A.B / (||A||*||B||)
        dot_product = np.dot(target_vector, other_vector)
        norm_product = np.linalg.norm(target_vector) * np.linalg.norm(other_vector)
        
        if norm_product == 0:
            sim = 0.0
        else:
            sim = float(dot_product / norm_product)
            
        similarities.append({
            "startup_name": name,
            "startup_website": startup.get("startup_website", "Not Mentioned"),
            "brief_description": desc,
            "similarity": round(sim, 4)
        })
        
    # Sort by similarity descending
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:top_k]
