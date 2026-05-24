📘 PROJECT_STRUCTURE.md
Directory Structure for Local AI Research System
1. Project Overview

โปรเจกต์นี้ถูกออกแบบให้เป็น

Local AI Multi-Agent Research Platform

ที่รองรับ

LLM reasoning
multi-agent collaboration
scientific tools
data analysis
model simulation

ดังนั้นโครงสร้าง project ต้องรองรับ

agents
tools
experiments
datasets
models
2. Recommended Directory Structure

โครงสร้าง project

AI-Agent-A1/
│
├─ main.py
├─ config.py
├─ requirements.txt
│
├─ agents/
│   ├─ planner_agent.py
│   ├─ critic_agent.py
│   └─ base_agent.py
│
├─ tools/
│   ├─ rice_blast_model.py
│   ├─ climate_analysis.py
│   ├─ data_analysis.py
│   └─ simulation_tools.py
│
├─ models/
│   └─ model_config.py
│
├─ experiments/
│   ├─ test_reasoning.py
│   ├─ test_tools.py
│   └─ benchmark_agents.py
│
├─ data/
│   ├─ climate/
│   ├─ disease/
│   └─ processed/
│
├─ notebooks/
│   └─ research_exploration.ipynb
│
├─ logs/
│   └─ runtime_logs.txt
│
└─ docs/
    ├─ SYSTEM_ARCHITECTURE.md
    ├─ SYSTEM_DIAGRAM.md
    ├─ DEVELOPMENT_LOG.md
    ├─ RESEARCH_SYSTEM_ROADMAP.md
    ├─ TOOLS_LAYER_ARCHITECTURE.md
    └─ PROJECT_STRUCTURE.md
3. Root Files
main.py

Entry point ของระบบ

หน้าที่

initialize agents
run reasoning loop
connect tools

Example

Planner → Critic → Refinement
config.py

ไฟล์ configuration

Example

model name
ollama endpoint
token limits
tool settings

Example

MODEL_NAME = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434"
MAX_TOKENS = 512
requirements.txt

Python dependencies

Example

pyautogen
ollama
numpy
pandas
matplotlib
4. Agents Directory

โฟลเดอร์นี้เก็บ agent logic

agents/

Example structure

agents/
 ├─ planner_agent.py
 ├─ critic_agent.py
 └─ base_agent.py
planner_agent.py

หน้าที่

generate explanations
propose hypotheses
invoke tools
critic_agent.py

หน้าที่

evaluate reasoning
identify weaknesses
suggest improvements
base_agent.py

agent base class

ใช้ shared functionality

model connection
message formatting
logging
5. Tools Directory

โฟลเดอร์นี้เก็บ computational tools

tools/

Example structure

tools/
 ├─ rice_blast_model.py
 ├─ climate_analysis.py
 ├─ data_analysis.py
 └─ simulation_tools.py
rice_blast_model.py

Example

infection risk model

Function

estimate disease risk
climate_analysis.py

Example

temperature trends
humidity patterns
rainfall distribution
data_analysis.py

Example

dataset analysis
statistical inference

Libraries

pandas
numpy
simulation_tools.py

Example

disease spread simulation
epidemiological models
6. Models Directory

โฟลเดอร์สำหรับ

model configuration

Example

models/
 └─ model_config.py

Example

MODEL = "qwen2.5:7b"
TEMPERATURE = 0.2
MAX_TOKENS = 512
7. Experiments Directory

เก็บ

testing scripts
benchmarks

Structure

experiments/
 ├─ test_reasoning.py
 ├─ test_tools.py
 └─ benchmark_agents.py

Example usage

measure latency
test agent reasoning
evaluate tool outputs
8. Data Directory

เก็บ dataset

data/

Example structure

data/
 ├─ climate/
 ├─ disease/
 └─ processed/

Possible datasets

weather records
disease incidence reports
crop monitoring data
9. Notebooks Directory

ใช้สำหรับ

exploratory research

Structure

notebooks/
 └─ research_exploration.ipynb

Use cases

data exploration
model prototyping
visualization
10. Logs Directory

เก็บ runtime logs

logs/

Example

runtime_logs.txt

Logs include

agent responses
tool calls
runtime performance
11. Documentation Directory
docs/

Documentation files

SYSTEM_ARCHITECTURE.md
SYSTEM_DIAGRAM.md
DEVELOPMENT_LOG.md
RESEARCH_SYSTEM_ROADMAP.md
TOOLS_LAYER_ARCHITECTURE.md
PROJECT_STRUCTURE.md

Purpose

document system design
track development
define architecture
12. Development Workflow

Typical development flow

Modify agents
 ↓
Test tools
 ↓
Run experiments
 ↓
Analyze results
 ↓
Update documentation
13. Scaling the Project

โครงสร้างนี้รองรับการขยาย

Example expansions

New agents
New tools
New datasets
Simulation modules

Future directories

vector_db/
pipelines/
visualization/
14. Example System Execution

Typical execution

python main.py

Workflow

User question
 ↓
Planner agent
 ↓
Tool invocation
 ↓
Critic agent
 ↓
Refined output
📌 Summary

โครงสร้าง project นี้ออกแบบให้รองรับ

LLM reasoning
tool-augmented AI
scientific research workflows

โดยสามารถขยายไปสู่

AI-assisted research platform

ได้ในอนาคต