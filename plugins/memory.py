"""
Pluggable Long-Term Memory System for Chat Applications

Implements a multi-tiered memory architecture:
- Working Memory: Current conversation context
- Episodic Memory: Historical interactions and experiences
- Semantic Memory: Facts and knowledge about users
- Procedural Memory: Learned patterns and preferences

Uses ChromaDB for vector storage and Google Gemini for reflection/analysis.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib
import time

import chromadb
from chromadb.config import Settings
import google.generativeai as genai


@dataclass
class Memory:
    """Base memory structure"""
    id: str
    content: str
    memory_type: str  # working, episodic, semantic, procedural
    timestamp: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class MemoryInterface(ABC):
    """Abstract interface for memory implementations"""

    @abstractmethod
    def add_memory(self, content: str, memory_type: str, metadata: Dict) -> str:
        """Add a new memory"""
        pass

    @abstractmethod
    def search_memories(self, query: str, memory_types: List[str], limit: int) -> List[Memory]:
        """Search memories by similarity"""
        pass

    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieve specific memory by ID"""
        pass

    @abstractmethod
    def update_memory(self, memory_id: str, updates: Dict) -> bool:
        """Update existing memory"""
        pass

    @abstractmethod
    def consolidate_memories(self) -> Dict[str, Any]:
        """Consolidate and organize memories"""
        pass


class AgenticMemorySystem(MemoryInterface):
    """
    Main memory system implementation using ChromaDB and Gemini
    """

    def __init__(
            self,
            persist_directory: str = "./memory_store",
            gemini_api_key: Optional[str] = None,
            collection_name: str = "chat_memories"
    ):
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )

        # Initialize Gemini for reflection
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.reflection_model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.reflection_model = None

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory"""
        timestamp = str(time.time())
        return hashlib.md5(f"{content}{timestamp}".encode()).hexdigest()[:16]

    def add_memory(self, content: str, memory_type: str, metadata: Dict = None) -> str:
        """Add new memory to the system"""
        metadata = metadata or {}
        memory_id = self._generate_id(content)

        # Add memory type and timestamp to metadata
        metadata.update({
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        })

        # Store in ChromaDB
        self.collection.add(
            documents=[content],
            ids=[memory_id],
            metadatas=[metadata]
        )

        return memory_id

    def search_memories(
            self,
            query: str,
            memory_types: Optional[List[str]] = None,
            limit: int = 5
    ) -> List[Memory]:
        """Search memories by semantic similarity"""
        # Build where clause for filtering
        where = None
        if memory_types:
            where = {"memory_type": {"$in": memory_types}}

        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where
        )

        # Convert to Memory objects
        memories = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                memory = Memory(
                    id=results['ids'][0][i],
                    content=results['documents'][0][i],
                    memory_type=results['metadatas'][0][i].get('memory_type', 'unknown'),
                    timestamp=results['metadatas'][0][i].get('timestamp', ''),
                    metadata=results['metadatas'][0][i]
                )
                memories.append(memory)

                # Update access count
                self._increment_access_count(memory.id)

        return memories

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get specific memory by ID"""
        try:
            result = self.collection.get(ids=[memory_id])
            if result['ids']:
                return Memory(
                    id=result['ids'][0],
                    content=result['documents'][0],
                    memory_type=result['metadatas'][0].get('memory_type', 'unknown'),
                    timestamp=result['metadatas'][0].get('timestamp', ''),
                    metadata=result['metadatas'][0]
                )
        except:
            return None

    def update_memory(self, memory_id: str, updates: Dict) -> bool:
        """Update existing memory metadata"""
        try:
            # Get current memory
            current = self.collection.get(ids=[memory_id])
            if not current['ids']:
                return False

            # Update metadata
            metadata = current['metadatas'][0]
            metadata.update(updates)
            metadata['last_updated'] = datetime.now().isoformat()

            # Update in ChromaDB
            self.collection.update(
                ids=[memory_id],
                metadatas=[metadata]
            )
            return True
        except:
            return False

    def _increment_access_count(self, memory_id: str):
        """Increment access count for memory"""
        current = self.collection.get(ids=[memory_id])
        if current['ids']:
            metadata = current['metadatas'][0]
            metadata['access_count'] = metadata.get('access_count', 0) + 1
            self.collection.update(ids=[memory_id], metadatas=[metadata])

    def consolidate_memories(self) -> Dict[str, Any]:
        """Consolidate working memories into long-term storage"""
        # Get all working memories
        working_memories = self.collection.get(
            where={"memory_type": "working"}
        )

        if not working_memories['ids']:
            return {"consolidated": 0, "created": []}

        consolidation_results = {
            "consolidated": 0,
            "created": []
        }

        # Use reflection to extract insights
        if self.reflection_model and len(working_memories['documents']) > 0:
            insights = self._reflect_on_memories(working_memories['documents'])

            # Create semantic and episodic memories from insights
            for insight in insights:
                if insight['type'] == 'fact':
                    memory_id = self.add_memory(
                        content=insight['content'],
                        memory_type='semantic',
                        metadata={'source': 'consolidation', 'confidence': insight.get('confidence', 0.8)}
                    )
                    consolidation_results['created'].append(memory_id)
                elif insight['type'] == 'experience':
                    memory_id = self.add_memory(
                        content=insight['content'],
                        memory_type='episodic',
                        metadata={'source': 'consolidation', 'importance': insight.get('importance', 'medium')}
                    )
                    consolidation_results['created'].append(memory_id)

        # Archive old working memories
        for memory_id in working_memories['ids']:
            self.update_memory(memory_id, {'archived': True})
            consolidation_results['consolidated'] += 1

        return consolidation_results

    def _reflect_on_memories(self, memories: List[str]) -> List[Dict]:
        """Use LLM to reflect on memories and extract insights"""
        if not self.reflection_model:
            return []

        prompt = f"""Analyze these conversation memories and extract key insights.

Memories:
{chr(10).join(memories)}

Extract:
1. Important facts about the user (semantic memory)
2. Significant experiences or interactions (episodic memory)
3. Patterns in preferences or behavior (procedural memory)

Return as JSON array with format:
[{{"type": "fact|experience|pattern", "content": "...", "confidence": 0.0-1.0, "importance": "low|medium|high"}}]
"""

        try:
            response = self.reflection_model.generate_content(prompt)
            # Parse JSON response
            insights = json.loads(response.text)
            return insights
        except:
            return []


class MemoryPlugin:
    """
    Plugin class to integrate memory system with chat applications
    Provides simple interface for chat apps to use memory features
    """

    def __init__(self, memory_system: MemoryInterface):
        self.memory = memory_system
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def process_message(self, role: str, content: str, user_id: str = "default") -> None:
        """Process a chat message and store in working memory"""
        self.memory.add_memory(
            content=f"[{role}]: {content}",
            memory_type="working",
            metadata={
                "user_id": user_id,
                "session_id": self.current_session_id,
                "role": role
            }
        )

    def get_relevant_context(self, query: str, limit: int = 3) -> str:
        """Get relevant memories as context for the current query"""
        # Search across different memory types
        memories = []

        # Get semantic memories (facts)
        semantic = self.memory.search_memories(query, ["semantic"], limit=limit)
        memories.extend(semantic)

        # Get episodic memories (experiences)
        episodic = self.memory.search_memories(query, ["episodic"], limit=limit)
        memories.extend(episodic)

        # Get procedural memories (patterns)
        procedural = self.memory.search_memories(query, ["procedural"], limit=1)
        memories.extend(procedural)

        # Format as context
        if not memories:
            return ""

        context_parts = []
        if semantic:
            context_parts.append("Known facts:\n" + "\n".join(f"- {m.content}" for m in semantic))
        if episodic:
            context_parts.append("Past interactions:\n" + "\n".join(f"- {m.content}" for m in episodic))
        if procedural:
            context_parts.append("User preferences:\n" + "\n".join(f"- {m.content}" for m in procedural))

        return "\n\n".join(context_parts)

    def end_session(self) -> Dict[str, Any]:
        """End current session and consolidate memories"""
        results = self.memory.consolidate_memories()
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return results

    def get_user_profile(self, user_id: str) -> Dict[str, List[str]]:
        """Get user profile from semantic memories"""
        facts = self.memory.search_memories(
            query=f"user {user_id}",
            memory_types=["semantic"],
            limit=10
        )

        preferences = self.memory.search_memories(
            query=f"user {user_id} preferences",
            memory_types=["procedural"],
            limit=5
        )

        return {
            "facts": [m.content for m in facts],
            "preferences": [m.content for m in preferences]
        }