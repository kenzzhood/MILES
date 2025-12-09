# MILES - Multimodal Intelligent Assistant

MILES is a next-generation cognitive agent framework that uses a **Microservice Architecture** to integrate specialized AI tools (3D Generation, RAG Search) under a central LLM Orchestrator.

## Key Features

1.  **Central Orchestrator**: Uses Gemini 1.5 Pro to "think", plan, and delegate tasks to specialized workers.
2.  **3D Generation**: Fully automated **Text-to-3D** (Image-to-3D) pipeline using **Stable Fast 3D (SF3D)**.
    -   Runs as a **local background service** (ComfyUI backend).
    -   Includes automatic background removal (`rembg`).
    -   Generates high-quality GLB models in <1 minute.
3.  **RAG Search**: Performs deep web searches for factual information when the LLM lacks context.
4.  **Asynchronous Architecture**: Built on FastAPI, Celery, and Redis for non-blocking task execution.

## Installation

### Prerequisites
-   **Windows 10/11**
-   **NVIDIA GPU** (4GB+ VRAM recommended, tested on RTX 3050)
-   **Redis Server** (Installed and running)

### Steps

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/kenzzhood/MILES.git
    cd MILES
    ```

2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup SF3D Portable**:
    -   The project relies on the "StableFast3D-WinPortable" package located at `src/libs/SF3D_Portable`.
    -   Ensure the `SF3D.7z` is extracted and `run.bat` exists in `src/libs/SF3D_Portable/SF3D/SF3D/`.

4.  **Configure Environment**:
    -   Create a `.env` file or update `src/config.py` with your `GEMINI_API_KEY`.

## Usage

We provide a single startup script to launch the backend, worker, and background 3D service.

1.  **Run the Starter Script**:
    ```bash
    start_miles.bat
    ```
    This will:
    -   Start the **Celery Worker** (minimized).
    -   Start the **FastAPI Orchestrator** (which auto-launches the hidden SF3D service).

2.  **Access the Web UI**:
    -   Open http://localhost:8000/ui
    -   Start chatting!

## Example Prompts

-   "Generate a 3D model from this image: E:\path\to\axe.png"
-   "Research the history of holography."
-   "Explain quantum computing and then generate a model of a quantum chip from this image..."

## Architecture

-   `src/orchestrator/`: The LLM "Brain" logic.
-   `src/services/sf3d_service.py`: Manages the local ComfyUI background process.
-   `src/workers/`: Celery tasks for disparate jobs.
-   `src/web/`: Static frontend with 3D Model Viewer (`<model-viewer>`).
