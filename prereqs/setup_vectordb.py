"""
Vector Database Setup Module

This module provides functionality to initialize and configure a ChromaDB vector database
with Google Gemini embeddings for semantic search and retrieval operations.

Dependencies:
    - chromadb: Vector database library
    - google-generativeai: For Gemini embedding generation
    - pyprojroot: Project root path management
    - dotenv: Environment variable management
    - box: Configuration management
    - yaml: Configuration file parsing

Configuration File:
    Reads from .config.yml in the project root containing:
    - db.vector.dir: Vector database directory path
    - db.vector.file: Vector database file name
    - vectordb_config.embedding_model: Gemini embedding model name
    - vectordb_config.collection_name: Collection name for storing vectors

Environment Variables Required:
    - GEMINI_API_KEY: Google Gemini API key for embedding generation
"""

import os
from box import Box
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pyprojroot import here
import yaml

# Load environment variables from .env file
load_dotenv()

# Load configuration from the YAML file using Box for easy access
with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))


def prepare_vector_db():
    """
    Prepares a vector database using ChromaDB and Google Gemini embeddings.

    This function sets up a vector database by:
    - Loading configuration from the YAML config file
    - Creating a Google Gemini embedding function using the provided API key and model
    - Creating the vector database directory if it doesn't exist
    - Initializing a persistent ChromaDB client at the specified directory
    - Creating or retrieving a collection in the vector database with cosine similarity

    Configuration Usage:
    - config.db.vector.dir: Base directory for vector database storage
    - config.db.vector.file: Database file name
    - config.vectordb_config.embedding_model: Gemini model for embeddings
    - config.vectordb_config.collection_name: Name of the vector collection

    Steps performed:
        1. Load Gemini API key and model name from environment and configuration
        2. Create a vector database directory if it doesn't already exist
        3. Initialize a ChromaDB client with a persistent storage path
        4. Create or get an existing collection with the specified name and embedding function
        5. Log the creation and the number of items in the collection

    Vector Database Configuration:
        - Similarity Metric: Cosine similarity (HNSW algorithm)
        - Embedding Provider: Google Gemini (model specified in config)
        - Storage: Persistent local storage
        - Collection: Single collection for semantic search and retrieval

    Raises:
        OSError: If directory creation fails
        chromadb.errors.ChromaDBError: If database initialization fails
        ValueError: If GEMINI_API_KEY environment variable is not set
        FileNotFoundError: If .config.yml file is not found
        yaml.YAMLError: If the configuration file is malformed

    Returns:
        None

    Example:
        >>> prepare_vector_db()
        Directory vectordb/chroma.db was created.
        DB collection created: Collection(name=chat_history)
        DB collection count: 0
    """
    # Construct the full vector database path from configuration
    vector_db = f'{config.db.vector.dir}/{config.db.vector.file}'
    
    # Get Gemini API key from environment variables
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required but not set")
    
    # Initialize Google Gemini embedding function with API key and model configuration
    # This function will be used to convert text into vector embeddings using Gemini
    gemini_embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
        api_key=gemini_api_key,
        model_name=config.vectordb_config.embedding_model
    )
    
    # Create the vector database directory if it doesn't exist
    vector_db_dir = here(config.db.vector.dir)
    if not os.path.exists(vector_db_dir):
        try:
            # Create the full directory path including the database file path
            os.makedirs(here(vector_db))
            print(f"Directory {vector_db} was created.")
        except OSError as err:
            raise OSError(f"Failed to create directory '{vector_db}': {err}")
    
    # Initialize ChromaDB persistent client
    # This creates a local database that persists across sessions
    db_client = chromadb.PersistentClient(path=str(vector_db))
    
    # Create or retrieve the collection with the specified configuration
    # Uses cosine similarity for vector comparisons (optimal for text embeddings)
    db_collection = db_client.get_or_create_collection(
        name=config.vectordb_config.collection_name,
        embedding_function=gemini_embedding_function,
        metadata={"hnsw:space": "cosine"}  # Configure similarity metric for HNSW algorithm
    )
    
    return db_collection


if __name__ == "__main__":
    """
    Main execution block for standalone script usage.
    
    When run directly, this script will:
    1. Load environment variables from .env file
    2. Load configuration from .config.yml file
    3. Initialize the vector database with Gemini embeddings
    4. Create the necessary collection
    5. Display status information
    
    Prerequisites:
    - GEMINI_API_KEY environment variable must be set
    - .config.yml file must exist in project root with proper structure
    - Required dependencies must be installed
    
    Usage:
        python setup_vectordb.py
        
    This is useful for:
    - Initial project setup
    - Vector database initialization
    - Testing database connectivity with Gemini embeddings
    - Verifying configuration settings
    """
    try:
        collection = prepare_vector_db()
        print("✅ Vector database setup completed successfully!")
        print(f"📊 Collection name: {collection.name}")
        print(f"🔢 Current item count: {collection.count()}")
        print(f"🤖 Using embedding model: {config.vectordb_config.embedding_model}")
    except Exception as e:
        print(f"❌ Error setting up vector database: {e}")
        raise