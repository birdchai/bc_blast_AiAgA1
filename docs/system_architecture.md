📘 AI Research System Architecture
Local Multi-Agent Scientific Reasoning Platform

1. System Overview

ระบบนี้ถูกออกแบบเพื่อสร้าง AI-assisted research environment ที่สามารถวิเคราะห์ปัญหาทางวิทยาศาสตร์ผ่านการทำงานร่วมกันของหลาย agent
กรณีศึกษาที่ใช้พัฒนา:
Rice blast disease (Magnaporthe oryzae)
วัตถุประสงค์หลักของระบบ

Generate scientific explanation
Critique reasoning
Refine hypotheses
Support research analysis

ระบบถูกออกแบบให้ทำงานแบบ

Fully local inference
GPU accelerated
Multi-agent reasoning

โดยไม่ต้องพึ่ง cloud API

2. Hardware Architecture

Development node:

MSI GS65

Hardware specification

CPU : Intel Core i7
GPU : NVIDIA GTX 1060 (6GB VRAM)
RAM : 24GB
Storage : NVMe SSD

GPU utilization during inference

GPU usage ≈ 98%
VRAM usage ≈ 4.7 / 6 GB
Temperature ≈ 70–76°C

Inference workload จึงทำงานบน GPU เต็มประสิทธิภาพ

3. Software Stack

Operating environment

Windows
Conda
Python 3.10

Environment

conda env: research-ai

Core components

Ollama
AutoGen (AgentChat)
Qwen2.5 7B
VS Code

Inference pipeline

AutoGen Agent
     ↓
OpenAIChatCompletionClient
     ↓
Ollama Local API
     ↓
Qwen2.5 7B Model

4. Model Architecture

Primary model

Qwen2.5 7B

Execution backend

Ollama
http://localhost:11434

Model configuration

context_window = 4096
max_output_tokens = 512

Optimization strategy

short prompts
token limitation
concise responses

Latency

≈10–16 seconds per inference

5. Agent Architecture

ระบบ reasoning ใช้ multi-agent collaboration

Current configuration

Planner Agent
Critic Agent

Roles

Planner

Generate mechanistic explanation
Formulate hypotheses

Critic

Evaluate explanation
Identify weaknesses
Suggest improvements

Agent interaction model

Planner v1
   ↓
Critic feedback
   ↓
Planner v2 refinement

6. Reasoning Workflow

System workflow

User query
   ↓
Planner Agent
   ↓
Critic Agent
   ↓
Planner Refine
   ↓
Final Explanation

Reasoning strategy

Critique-Refinement Loop

Purpose

Improve explanation quality
Reduce hallucination
Increase reasoning depth

7. System Data Flow

Data flow within the system

User Prompt
   ↓
AutoGen Agent
   ↓
LLM Inference (Ollama)
   ↓
Agent Output
   ↓
Critic Evaluation
   ↓
Refined Explanation

Context accumulation

Planner output
Critic feedback

ส่งเข้า refine stage

8. Performance Analysis

Single inference

10–16 sec

Full reasoning loop

Planner
Critic
Planner refine

Runtime

≈115 seconds

Primary bottleneck

context expansion
token accumulation

GPU performance

Fully utilized

9. System Limitations

Current limitations

Context growth

Agent communication increases token length

Reasoning accuracy

LLM may hallucinate biological details

Performance scaling

Multiple agents increase runtime

10. Future Extensions
Tool-augmented agents

Next stage

Agent + computational tools

Example tools

epidemiological model
climate analysis
disease risk estimation

Architecture

Agent
 ↓
Tool invocation
 ↓
Model result
 ↓
Scientific explanation
Domain expert agents

Planned agents

Plant pathology agent
Climate analysis agent
Spatial modeling agent

Purpose

improve scientific accuracy
specialized reasoning
Hybrid model system

Future optimization

Planner → 7B model
Critic → smaller model

Benefits

lower latency
higher agent count
reduced GPU load

11. System Capability Summary

Current system enables

Local LLM inference
Multi-agent reasoning
Scientific critique loops
Offline operation
GPU acceleration

The platform functions as a

Local AI Research Sandbox

for experimenting with

AI-assisted scientific discovery

12. Development Stage

Completed

Phase 1
Local LLM + Multi-Agent Reasoning

Next phase

Phase 2
Tool-Augmented Research Agents

Goal

Integrate computation and reasoning
📌 Final Note

This system represents the foundation of a

AI-assisted scientific research platform

capable of supporting

hypothesis generation
mechanistic reasoning
model analysis
scientific critique

within a fully local environment.