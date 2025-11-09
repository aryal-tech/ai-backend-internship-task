# AI/ML Internship Task: RAG and Booking Backend

This project is a complete backend solution for a document-aware conversational AI, built as part of an internship application task. It features two core REST APIs for document ingestion and a custom Retrieval-Augmented Generation (RAG) chat, including multi-turn memory and an LLM-powered interview booking system.

The entire application is containerized with Docker and designed with a clean, modular architecture, following modern Python standards with full type hinting and dependency injection.

## Features

### Document Ingestion API (`POST /ingest`)
-   **File Upload:** Accepts `.pdf` and `.txt` files.
-   **Text Extraction:** Reliably extracts text from digital PDFs and plain text files, with an optional OCR fallback for scanned PDFs.
-   **Selectable Chunking:** Implements two distinct chunking strategies:
    1.  `fixed`: A simple, token-based sliding window.
    2.  `semantic`: A more advanced sentence-aware strategy to preserve context.
-   **Vectorization & Storage:** Generates embeddings locally using a `fastembed` model and stores them in **Qdrant**.
-   **Metadata Persistence:** Saves document and chunk metadata in a **MySQL** database for relational integrity and tracking.

### Conversational RAG API (`POST /chat`)
-   **Custom RAG Pipeline:** Implemented from scratch without relying on high-level abstractions like LangChain's `RetrievalQAChain`, demonstrating a deep understanding of the RAG workflow.
-   **Multi-Turn Conversation:** Utilizes **Redis** to maintain chat history, enabling the model to understand context in follow-up questions.
-   **Local LLM Integration:** Powered by a groq for generation, ensuring privacy and zero external API costs for the core logic.
-   **Interview Booking:** The LLM can intelligently identify booking requests, extract `name`, `email`, `date`, and `time` from natural language, and store the confirmed booking in the MySQL database.

## Tech Stack

-   **Backend Framework:** FastAPI
-   **Web Server:** Uvicorn
-   **Containerization:** Docker & Docker Compose
-   **Vector Database:** Qdrant
-   **Metadata Database:** MySQL
-   **Chat Memory:** Redis
-   **Local Embeddings:** `fastembed` with `BAAI/bge-small-en-v1.5`
-   **LLM:**llama-3.1-8b-instant
-   **Data Validation:** Pydantic




## Setup and Installation

### Prerequisites
-   Docker and Docker Compose
-   Python 3.11+
-   Git

### 1. Clone the Repository
```bash
git clone <your-github-repo-link>
cd ai-backend
2. Configure Environment
Create a .env file in the root directory by copying the example.

Bash

# On Linux/macOS
cp .env.example .env

# On Windows
copy .env.example .env
(You will need to create the .env.example file first, see content below)

.env.example content:

text

# Embeddings (local via fastembed)
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIM=384

# LLM (local via Ollama)
LLM_PROVIDER=ollama
LLM_MODEL=phi3:medium
OLLAMA_HOST=http://localhost:11434

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=docs_local

# MySQL
MYSQL_ROOT_PASSWORD=change-me-root
MYSQL_DATABASE=ai_backend
MYSQL_USER=ai_user
MYSQL_PASSWORD=change-me-user
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306

# Redis
REDIS_URL=redis://localhost:6379/0
3. Start Services with Docker Compose
This command will start Qdrant, MySQL, Redis, and Ollama in detached mode.

Bash

docker compose up -d
4. Pull the Ollama LLM Model
Pull a capable model like phi3:medium or llama3 (recommended) inside the running Ollama container.

Bash

docker exec -it ollama ollama pull phi3:medium
5. Set Up Python Environment
Create a virtual environment and install the required packages.

Bash

# Create venv
python -m venv .venv

# Activate venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
6. Initialize Databases
Apply the MySQL schema and create the initial Qdrant collection.

Bash

# Apply MySQL schema
# On Linux/macOS:
cat scripts/init_mysql.sql | docker exec -i mysql mysql -uai_user -pchange-me-user ai_backend
# On Windows:
Get-Content .\scripts\init_mysql.sql | docker exec -i mysql mysql -uai_user -pchange-me-user ai_backend

# Create Qdrant collection (optional, the app will auto-create it)
python scripts/init_qdrant.py

**Running the Application
With all services running and the environment set up, start the FastAPI server:

Bash

uvicorn app.main:app --reload
The API will be available at http://127.0.0.1:8000. You can access the interactive documentation at http://127.0.0.1:8000/docs.

🧪 API Usage and Testing
Use curl or the /docs UI to test the endpoints.

1. Ingest a Document
Upload a .txt file.

Bash

curl -X POST "http://127.0.0.1:8000/ingest" \
  -F "file=@/path/to/your/document.txt" \
  -F "chunk_strategy=semantic"
2. Start a Conversation (RAG)
Ask a question about the document you just ingested.

Bash

curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the main policy described in the document?"
  }'
3. Continue the Conversation (Multi-Turn)
Use the conversation_id from the previous response to ask a follow-up question.

Bash

curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "and what about its implementation?",
    "conversation_id": "YOUR_CONVERSATION_ID_FROM_PREVIOUS_RESPONSE"
  }'
4. Book an Interview
Ask the bot to book an interview.

Bash

curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to book an interview for John Doe. His email is john.doe@example.com. How about next Tuesday at 3pm?"
  }'
You can then verify the new entry in the bookings table in your MySQL database.


Architectural Notes
Custom RAG Pipeline: The RAG logic in rag_service.py was built from the ground up, including question condensing for multi-turn context and prompt engineering for reliable instruction-following with local LLMs.
Robust Booking: The booking system uses a "prompt engineering" approach, instructing the LLM to return a specific JSON format. This avoids version-specific issues with the Ollama tools API and is more compatible across different models.
Separation of Concerns: The code is organized into services (business logic), repositories (data access), and api (HTTP layer), making it easy to test, maintain, and extend.
Dependency Injection: FastAPI's dependency injection system is used extensively to manage clients (DB sessions, Redis, etc.) and services, promoting clean and testable code.

