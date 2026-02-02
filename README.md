# PEARC 2026 Tutorial:  AI Agents for Scientific Computing 

The contents of this repo showcase the planned content for a 3 hour tutorial at PEARC. This tutorial consists of 5 parts:

1. Introduction to AI Agents
2. LAB: Introduction to TACC compute resources
3. LAB: Introduction to Building simple agents
4. LAB: Building agents for Data Analysis
5. LAB: Building agents for use in HPC environments

>[!NOTE]
> For Part (3) and Part (4): Dependencies are specified in the requirements.txt in this repo
> For Part (5): We will have an *additional* dependency called TACC_exAI (an experimental agent framework code developed at TACC which will be provided at a later date due to on going research)


## Environment setup instructions

### On TACC Resources

Detailed instructions for accessing TACC's compute resources and setting up your environment for the Labs 3-5 is included in the slide deck for Part (2).

### On your local machine

While this training will be conducted on TACC infrastructure, in the event of network issues at the venue, we are providing some general instructions
on setting up a workable environment on your local machines.

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
    * Download 2 models locally (qwen3:8b and qwen3:32b: *This will require about 26GB of free space*)
        * `ollama pull qwen3:8b`
        * `ollama pull qwen3:32b`
 

