# pearc26_tutorial_ai_agents
tutorial content for pearc 2026 tutorial on ai agents 

This tutorial consists of 3 parts:

1. Introduction to Building simple agents
2. Building agents for Data Analysis
3. Building agents for use in HPC environments

>[!NOTE]
> For Part (1) and Part (2): Dependencies are specified in the requirements.txt in this repo
> For Part (3): We will use have an *additional* dependency on TACC_exAI (an experimental agent framework code developed at TACC which will be provided)


## Environment setup instructions

### On TACC Resource (Vista)

1. Load an appropriate python module (choose a python version >= 3.9 and < 3.13)
```module load python3/3.11.8
```
OR

1. Container setup instructions <here>


### On your local machine

While this training will be conducted on TACC infrastructure, in the event of network issues at the venue, we are providing some general instructions
on setting up a workable environment on your local machines.

>[!CAUTION]
> We are unable to provide specific instructions/support for individual machines given that this would be highly dependent on your specific platform
> (i.e Hardware, Operating System and other tool chains). Please try and adapt the generic instructions provided to your specific machine

Other software dependencies:
>[!NOTE}
>  Please note that these are prerequisites and we expect them to be setup before the tutorial.
> Given the time constraints of the tutorial, we will be unable to pause instruciton to assist to provide additional support for installations issues individually
1. Install Ollama
2. Install Jupyter notebook
3. Install an appropriate python version (choose a python version >= 3.9 and < 3.13)
4. Install python package/environment manager of choice (uv or pip)
 

1. Create a python environment
``` uv venv <environment name>
```
For example:
``` uv venv pearc26_tutorial
```
2. Activate the virtual environment
```source pearc26_tutorial/bin/activate
```

3. Install dependencies (specified in the requirements.txt file)
``` uv pip install -r requirements.txt
```

