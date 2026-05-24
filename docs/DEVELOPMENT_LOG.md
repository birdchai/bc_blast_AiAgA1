📘 DEVELOPMENT_LOG.md
Local AI Multi-Agent Research System
Project Development Log

Project:

Local AI Multi-Agent Research System

Research Topic:

Rice blast disease (Magnaporthe oryzae)

Development Environment:

Local GPU inference
Phase 0 — Environment Setup
Objective

เตรียมระบบสำหรับรัน LLM แบบ local

Hardware
Machine : MSI GS65
GPU     : NVIDIA GTX 1060
VRAM    : 6 GB
RAM     : ~24 GB
Software
Windows
Conda
Python 3.10
VS Code

Environment

conda env: research-ai

Validation

python -c "import sys; print(sys.executable)"

Result

Environment configured successfully
Phase 1 — Local LLM Deployment
Objective

ติดตั้งและรัน LLM แบบ local

Model
Qwen2.5 7B

Backend

Ollama

Model pull

ollama pull qwen2.5:7b

Inference test

ollama run qwen2.5:7b

Result

Local LLM inference successful
Phase 2 — AutoGen Integration
Objective

เชื่อม AutoGen กับ Ollama

Components

AutoGen AgentChat
OpenAIChatCompletionClient
Ollama API

Connection

http://localhost:11434

Test script

main.py

Validation

Agent successfully communicates with local LLM
Phase 3 — GPU Inference Optimization
Objective

ทำให้ inference ใช้ GPU เต็มประสิทธิภาพ

Monitoring tool

Windows Task Manager

Observed metrics

GPU usage ≈ 98%
VRAM usage ≈ 4.7 / 6 GB
Temperature ≈ 70–76°C

Inference latency

~41 seconds (initial)

Optimization applied

Reduce token output
Shorten prompts
Limit max_output_tokens

Improved latency

~10–16 seconds
Phase 4 — Multi-Agent Reasoning
Objective

สร้างระบบ reasoning ที่ใช้หลาย agent

Architecture

Planner Agent
Critic Agent

Roles

Planner

Generate mechanistic explanation

Critic

Evaluate reasoning
Identify weaknesses

Workflow

Planner v1
   ↓
Critic Feedback
   ↓
Planner v2 Refinement

Implementation

AutoGen AssistantAgent
Phase 5 — Scientific Reasoning Test
Test problem
Mechanistic infection process of rice blast

Planner output

Initial explanation of infection cycle

Critic output

Identified biological gaps
Suggested improvements

Planner refinement

Expanded mechanistic explanation

Result

Reasoning improved through critique loop
Phase 6 — Performance Measurement

Measured runtime

Single inference : 10–16 sec

Full reasoning loop

Planner
Critic
Planner refine

Total runtime

≈ 115 seconds

Observed bottleneck

Context expansion
Token accumulation
Phase 7 — System Capability

Current system supports

Local LLM inference
GPU acceleration
Multi-agent reasoning
Critique-refinement workflow
Offline execution

System classification

Local AI Research Sandbox
Phase 8 — Key Engineering Insights
GPU
Fully utilized
Performance bottleneck
Context length
Optimization strategy
Prompt control
Agent specialization
Token limitation
System scaling challenge
Agent communication increases context size
Phase 9 — Next Development Stage

Next objective

Tool-Augmented Agents

Agents will interact with

Python functions
Scientific models
Data analysis tools

Example tools

Rice blast epidemiological model
Climate data analysis
Disease risk estimation

Future architecture

Agent reasoning
+
Computational tools
Phase 10 — Long-Term Vision

Target system

AI-assisted scientific research platform

Capabilities

Hypothesis generation
Mechanistic reasoning
Model evaluation
Data analysis
Scientific critique

Potential research application

Plant disease modeling
Agricultural epidemiology
Climate-disease interaction
Development Status

Current stage

Phase 1 completed
Local Multi-Agent Reasoning System

Next stage

Phase 2
Tool-augmented AI agents
Final Note

The project has successfully established a

Fully local AI multi-agent research environment

capable of supporting early-stage AI-assisted scientific reasoning workflows.