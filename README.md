<p align="center">
  <img src="assets/banner.png" alt="MILES Banner" width="100%">
</p>

<h1 align="center">MILES</h1>
<p align="center">
  <strong>Multimodal Intelligent Agent System</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Gemini_1.5_Pro-8E75B2?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=threedotjs&logoColor=white" alt="ThreeJS">
</p>

> **MILES** is a next-generation cognitive agent framework leveraging a robust **Microservice Architecture**. It integrates specialized AI capabilities—such as advanced 3D generation and RAG search—under a centralized LLM Orchestrator that "thinks", plans, and executes.

---

## ✨ Features

- 🧠 **Centralized Intelligence Core:** Powered by Gemini 1.5 Pro to intelligently delegate tasks, manage context, and coordinate disparate microservices.
- 🧊 **Accelerated 3D Generation Pipeline:** Fully automated Text-to-3D (Image-to-3D) workflows via **Stable Fast 3D (SF3D)** running as a dedicated local background service. Generates high-quality GLB assets in under 60 seconds with built-in background removal.
- 🖐️ **Holographic 3D Interactive Viewer:** Premium dark-themed UI relying on customized `Three.js` integration, implementing ultra-smooth hand-tracking (via MediaPipe homography) to dynamically rotate, scale, and manipulate 3D models exactingly. 
- 🔎 **Intelligent Deep RAG Strategy:** Real-time factual augmentation using integrated web search to build execution context unavailable in static models.
- ⚡ **Asynchronous Microservice Backbone:** Blazing fast execution built around FastAPI, Celery queues, and Redis for distributed, non-blocking task orchestration.

---

## 🏗️ Architecture

MILES adopts an event-driven, microservices-oriented topology to separate concerns and ensure scalability between the brain, memory, and task execution instances.

```mermaid
graph TD
    User["👤 User (Web Dashboard / 3D UI)"] -->|WebSocket / HTTP| Orchestrator
    
    subgraph "Core Nervous System"
        Orchestrator["🧠 LLM Orchestrator (FastAPI / Gemini)"]
        Redis["🗄️ Redis Broker"]
        CeleryWorker["⚙️ Celery Worker Pool"]
    end
    
    subgraph "Specialized Services"
        3DService["🧊 SF3D Local Service (ComfyUI)"]
        RAGService["🔎 Search & RAG Tools"]
        HandTracking["🖐️ WebCam / UDP Hand Tracking"]
    end
    
    Orchestrator -->|Enqueues Tasks| Redis
    Redis -->|Dispatches| CeleryWorker
    CeleryWorker -->|Calls API| 3DService
    CeleryWorker -->|Executes| RAGService
    HandTracking -.->|Controls View| User
```

### Component Architecture
- `src/orchestrator/`: The core cognitive loop. Processes incoming user context, routes workflow tools, and manages memory limits.
- `src/services/sf3d_service.py`: Dedicated abstraction layer to control the native ComfyUI process serving SF3D queries.
- `src/workers/`: Heavy-lifting Celery processes executing computationally or time-intensive generative pipelines.
- `src/web/`: Aesthetically premium, reactive web frontend and 3D modeling environments.

---

## 🚀 Getting Started

### Prerequisites
- **OS:** Windows 10/11
- **Hardware:** NVIDIA GPU (Recommended: 4GB+ VRAM for continuous local generation; validated on RTX 3050).
- **Core Dependencies:** Local Redis Server instance required and active.

### Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/MILES.git
   cd MILES
   ```

2. **Environment Assembly:**
   Deploy the Python specifications using the unified constraints list:
   ```bash
   pip install -r requirements.txt
   ```

3. **Vendor Setup (SF3D Portable):**
   - MILES intrinsically runs operations atop `StableFast3D-WinPortable` localized in `src/libs/SF3D_Portable`.
   - Before firing up, unpack the provided `.7z` so that `run.bat` is resolvable inside the extracted directory root.

4. **Configuration:**
   - Mount your API keys and parameters inside a local `.env` file or hardcode them safely into `src/config.py`.

### Execution Flow

A packaged initialization script seamlessly brings the API, workers, and background generation processes online. 

1. **Spin up MILES:**
   ```bash
   start_miles.bat
   ```
   *This automatically engages and minimizes the Celery background nodes, mounts the overarching FastAPI network, and bridges to the hidden ComfyUI process.*

2. **Engage the Interface:**
   - Navigate to `http://localhost:8000/ui` in your browser.
   - Command tasks using natural language, or explore models leveraging your physical hands!

---

## 🔮 Usage Examples

*Examples to prompt the intelligent orchestrator:*
- *"Ingest this URL and isolate a 3D model of the focal object: `C:\path\to\reference.png`."*
- *"Look up the origin and implementation complexities of MonoSplat."*
- *"Deploy a holographic rendering of a cyberpunk drone; map its engine specs based on theoretical design papers."*

---
> *Developed as a bleeding-edge deployment of Agentic AI paradigms interwoven with localized generative pipelines and immersive interface manipulation capabilities.*
