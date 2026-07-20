# models/slurm.py
from pydantic import BaseModel, Field, validator
from typing import Literal

class GenerateSlurmScript(BaseModel):
    thoughts: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Reasoning steps and assumptions about the Slurm job."
    )
    partition: Literal["gg", "gh", "gh-dev"] = Field(
        ...,
        description=(
            "Requested Slurm partition; must be one of gg, gh, gh-dev."
            " gg has two grace cpus per node, gh has one grace cpu, one"
            " hopper gpu, gh-dev is same hardware as gh but with a 2 hour"
            " time limit and is meant for software development."
        )
    )
    time: str = Field(
        ...,
        #pattern=r"^\d{2}:\d{2}:\d{2}$",
        description="Walltime in HH:MM:SS format, with a maximum of 48:00:00."
    )
    job_name: str = Field(
        ...,
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        description="A short Slurm job name derived from the user task."
    )
    num_nodes: int = Field(
        1,
        ge=1,
        le=512,
        description="Number of nodes requested."
    )
    ntasks_per_node: int = Field(
        1,
        ge=1,
        le=4,
        description="Number of tasks per node."
    )
    script_filename: str = Field(
        ...,
        strip_whitespace=True,
        min_length=1,
        max_length=255,
        description="Filename to save the Slurm script as, e.g., run_job.sh."
    )
    slurm_script_body: str = Field(
        ...,
        description="Slurm script body and job steps that appear under the SBATCH directives in the script. DO NOT include SBATCH directives here; only the commands to run the user's task and any necessary setup steps."
    )

    @validator("time")
    def validate_time_max_48h(cls, v: str) -> str:
        hh, mm, ss = map(int, v.split(":"))
        total_seconds = hh * 3600 + mm * 60 + ss
        if total_seconds > 48 * 3600:
            raise ValueError("time must be <= 48:00:00 (48 hours)")
        return v
