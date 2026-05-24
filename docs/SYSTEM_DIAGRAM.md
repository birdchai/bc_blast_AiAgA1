📘 SYSTEM_DIAGRAM.md
Local AI Multi-Agent Research System
1. System Overview

ระบบนี้ถูกออกแบบเป็น Local AI Research Platform ที่ใช้ Large Language Model และ Multi-Agent Reasoning เพื่อช่วยวิเคราะห์ปัญหาทางวิทยาศาสตร์

ระบบทำงานแบบ

Fully Local
GPU Accelerated
Multi-Agent Reasoning
Tool-Augmented AI

กรณีศึกษาหลัก

Rice blast disease (Magnaporthe oryzae)
2. High-Level Architecture

ภาพรวมระบบ

             ┌─────────────────────┐
             │        User         │
             └─────────┬───────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │    Planner Agent    │
             │  (Scientific Logic) │
             └─────────┬───────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │     Critic Agent    │
             │  (Scientific Review)│
             └─────────┬───────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │   Planner Refinement│
             └─────────┬───────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │   Final Explanation │
             └─────────────────────┘
3. LLM Execution Pipeline

LLM inference pipeline

AutoGen Agent
      │
      ▼
OpenAIChatCompletionClient
      │
      ▼
Ollama Local API
      │
      ▼
Qwen2.5 7B Model
      │
      ▼
GPU Inference (CUDA)

Runtime environment

GPU: GTX 1060
VRAM usage ≈ 4.7 GB
GPU utilization ≈ 98%
4. Agent Interaction Diagram

Multi-Agent reasoning workflow

User Prompt
     │
     ▼
Planner Agent
     │
     │ Generate explanation
     ▼
Critic Agent
     │
     │ Identify weaknesses
     ▼
Planner Agent
     │
     │ Improve reasoning
     ▼
Final Output

Reasoning strategy

Critique → Refinement Loop

Purpose

Increase reasoning depth
Reduce hallucination
Improve scientific explanation
5. Internal Data Flow

Data flow within the system

User Query
    │
    ▼
Planner v1 Output
    │
    ▼
Critic Feedback
    │
    ▼
Planner Refinement Prompt
    │
    ▼
Final Explanation

Context accumulation

Planner Output
+
Critic Feedback
=
Refinement Prompt
6. Performance Characteristics

Single inference latency

≈ 10–16 seconds

Full reasoning loop

Planner
Critic
Planner refine

Runtime

≈ 115 seconds

Primary bottleneck

Context expansion
Token accumulation
7. Hardware Utilization

System resource usage during inference

GPU

Utilization ≈ 98%
VRAM ≈ 4.7 / 6 GB
Temperature ≈ 70–76°C

CPU

≈ 40–50%

RAM

≈ 13 GB usage

Inference therefore runs primarily on GPU compute.

8. Planned Tool-Augmented Architecture

Next development stage integrates computational tools

Future architecture

             ┌─────────────┐
             │    Planner  │
             └──────┬──────┘
                    │
                    ▼
            ┌───────────────┐
            │  Tool Layer   │
            │ (Python tools)│
            └──────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │ Model Results  │
           └──────┬─────────┘
                  │
                  ▼
             ┌─────────────┐
             │   Critic    │
             └─────────────┘

Tools may include

epidemiological models
climate analysis
disease risk estimation
data processing
9. Future Agent Expansion

Planned specialized agents

Plant Pathology Agent
Climate Analysis Agent
Spatial Modeling Agent
Data Analysis Agent
Simulation Agent

Architecture

Domain Expert Agents
        │
        ▼
Collaborative Reasoning
10. Hybrid Model Architecture (Future)

To improve performance

Planner Agent → Qwen2.5 7B
Critic Agent → smaller model

Benefits

lower latency
reduced GPU load
more agents possible
11. System Role

The system functions as a

Local AI Research Sandbox

capable of supporting

scientific reasoning
hypothesis generation
model critique
mechanistic explanation

without requiring external API services.

12. Development Roadmap

Current stage

Phase 1
Local LLM + Multi-Agent Reasoning

Next stage

Phase 2
Tool-Augmented AI Agents

Long-term goal

AI-assisted plant disease research platform