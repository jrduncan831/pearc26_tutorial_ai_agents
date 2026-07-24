# PEARC 2026 Tutorial:  AI Agents for Scientific Computing 

The contents of this repo showcase the planned content for a 3 hour tutorial at PEARC. This tutorial consists of 5 parts:

1. Introduction to AI Agents
2. LAB: Introduction to TACC compute resources
3. LAB: Introduction to building simple agents
4. LAB: Building agents for data analysis
5. LAB: Building agents for use in HPC environments

>[!NOTE]
> A containerized kernel with all required models and dependencies will be provided on TACC systems at the beginning of the course. In the event of an internet outage, please follow one of the local installation instructions below before the course.


## Environment setup instructions

### On TACC Resources

This class requires an active and verified TACC account:
1. **If you do not have a TACC account, you must register for one [here](https://accounts.tacc.utexas.edu/register)**. This process involves verifying your email, agreeing to the TACC Acceptable Use Policy, and setting up multifactor authorization on your mobile device.
2. **All participants must submit their TACC username to this [Google form](https://docs.google.com/forms/d/e/1FAIpQLSfLOiGRIF4x0L2AXSZuDyqt1jN4Re0QsiKpz1oo_KQYQwoy_w/viewform)**. This form allows us to add you to the project allocation prior to the start of the tutorial.

Detailed instructions for accessing TACC's compute resources and setting up your environment for the Labs 3-5 is included in the slide deck for Part (2) and we will go over it together during the tutorial.


### Local Installation Instructions (Docker-Based)

If internet access is unavailable during the tutorial, you can use this Docker-based setup as the recommended local installation method for offline execution of the labs.

1. Install Docker Desktop
    * [Official Download](https://www.docker.com/products/docker-desktop/)
    * [Official Docker CLI documentation](https://docs.docker.com/reference/cli/docker/)
      
2. Install `git` command line client
    * [Official Install Instructions](https://git-scm.com/install/source)

3. Clone the repository:
   `git clone https://github.com/jrduncan831/pearc26_tutorial_ai_agents.git`

4. Navigate into the project directory:
   `cd pearc26_tutorial_ai_agents`

5. Run the installation script:
   `bash install.sh`

   This script will:
   - Pull a preconfigured Docker container that already includes:
     - Ollama installed and configured for local LLM management
     - Apptainer installed for sandboxed code execution
     - All required Python dependencies for the tutorial
   - Download required models and assets:
     - LLMs: gemma3:27b and qwen3:8b
     - Embedding model: all-MiniLM-L6-v2
     - Apptainer container image: python_3.10-slim.sif

   Note: This process requires approximately 33GB of free disk space.

6. Launch the environment:
   `bash launch.sh`

   This will:
   - Start the containerized environment
   - Launch Jupyter Lab inside the container
   - Automatically open the interface in your default web browser


### Local Installation Instructions (virtual environment)
If the above docker installation method does not work for you, below is information for building the environment from scratch.

>[!CAUTION]
> We are unable to provide specific instructions/support for individual machines given that this would be highly dependent on your specific platform
> (i.e Hardware, Operating System and other tool chains). Please try and adapt the generic instructions provided to your specific machine

Other software dependencies:
>[!NOTE]
>  Please note that these are prerequisites and we expect them to be setup before the tutorial.
> Given the time constraints of the tutorial, we will be unable to pause instruction to assist to provide additional support for installations issues individually

1. Install `git` command line client
    * [Official Install Instructions](https://git-scm.com/install/source)

2. Install `uv`
    * [Official Install Instructions](https://docs.astral.sh/uv/getting-started/installation/)

3. Install Python 3.12
    * `uv venv --python 3.12 pearc26_tutorial`

4. Activate python environment
    * `source pearc26_tutorial/bin/activate`

5. Install package dependencies (requirements.txt)
    * `uv pip install -r requirements.txt`

6. Install Docker Desktop
    * [Official Download](https://www.docker.com/products/docker-desktop/)
    * [Official Docker CLI documentation](https://docs.docker.com/reference/cli/docker/)
    * Download a container for sandboxed execution of agent code outputs
        * `docker pull python:3.10-slim`

7. Install Ollama
    * [Official Download](https://ollama.com/download)
    * [Official Install Instructions](https://docs.ollama.com)
    * Download 2 models locally (qwen3:8b and gemma3:27b: *This will require about 22GB of free space*)
        * `ollama pull qwen3:8b`
        * `ollama pull gemma3:27b`

 8. Download the text embedding model all-MiniLM-L6-v2 to use with the SentenceTransformer module
```bash
python - << "PY"
from sentence_transformers import SentenceTransformer

# This will download/cache the model into the HF_HOME/hub directory
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_ = model.encode(["test load"])
print("Downloaded and cached all-MiniLM-L6-v2.")
PY
```

