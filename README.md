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
> Given the time constraints of the tutorial, we will be unable to pause instruciton to assist to provide additional support for installations issues individually
1. Install Ollama
2. Install Jupyter notebook
3. Install an appropriate python version (choose a python version >= 3.9 and < 3.13)
4. Install python package/environment manager of choice (uv or pip)
 

1. Create a python environment
```
uv venv <environment name>
```
For example:
```
uv venv pearc26_tutorial
```
2. Activate the virtual environment
```
source pearc26_tutorial/bin/activate
```

3. Install dependencies (specified in the requirements.txt file)
```
uv pip install -r requirements.txt
```

