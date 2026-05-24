📘 AGENT_DESIGN_SPEC.md
Design Specification for AI Research Agents
1. Overview

ระบบนี้ใช้ multi-agent architecture เพื่อช่วยวิเคราะห์ปัญหาทางวิทยาศาสตร์

Agent ถูกออกแบบให้ทำงานเหมือน research team

ตัวอย่างบทบาท

Planner
Critic
Domain Experts
Tool Agents

Agent collaboration ช่วยให้ระบบ

improve reasoning quality
reduce hallucination
increase domain awareness
2. Agent Architecture

โครงสร้าง agent system

                ┌─────────────┐
                │   Planner   │
                └──────┬──────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     Tool Agents   Domain Agents   Critic
          │            │            │
          └────────────┴──────┬─────┘
                              ▼
                       Refined Output
3. Core Agent Roles

ระบบเริ่มต้นด้วย 2 core agents

Planner Agent
Critic Agent

และจะขยายในอนาคต

4. Planner Agent

Planner เป็น agent หลักของระบบ

Responsibilities

Interpret user question
Generate explanations
Propose hypotheses
Decide when to invoke tools

Planner ทำหน้าที่เหมือน

lead researcher

Workflow

User query
 ↓
Interpret problem
 ↓
Generate reasoning
 ↓
Invoke tools if necessary
 ↓
Produce explanation

Example tasks

Explain disease mechanisms
Analyze climate effects
Generate hypotheses
5. Critic Agent

Critic ทำหน้าที่

evaluate reasoning quality

Responsibilities

identify logical flaws
detect missing mechanisms
suggest improvements

Critic ทำหน้าที่เหมือน

peer reviewer

Workflow

Planner output
 ↓
Critic analysis
 ↓
Feedback generation

Example feedback

Missing molecular mechanisms
Incorrect biological assumptions
Incomplete environmental factors
6. Tool Agents

Tool agents เป็น interface สำหรับ computational tools

Responsibilities

run deterministic calculations
analyze data
simulate models

Examples

epidemiology model
climate analysis
data processing

Workflow

Planner request
 ↓
Tool execution
 ↓
Return model output

Example

Input
temperature = 27°C
humidity = 92%

Output
risk_level = High
7. Domain Expert Agents

Domain agents เพิ่ม specialized knowledge

Planned agents

Plant Pathology Agent
Climate Analysis Agent
Spatial Modeling Agent
Data Science Agent

Purpose

increase scientific accuracy
reduce hallucination
provide domain reasoning

Example workflow

Planner
 ↓
Plant Pathology Agent
 ↓
Climate Agent
 ↓
Critic
8. Agent Communication Model

Agents สื่อสารผ่าน structured messages

Example message flow

User Prompt
 ↓
Planner Response
 ↓
Critic Feedback
 ↓
Planner Refinement

Message types

Reasoning messages
Tool requests
Tool responses
Critique feedback
9. Reasoning Strategy

ระบบใช้ reasoning strategy

Critique → Refinement Loop

Workflow

Planner v1
 ↓
Critic evaluation
 ↓
Planner v2

Advantages

improved reasoning quality
reduced hallucination
deeper analysis
10. Tool Invocation Strategy

Planner ตัดสินใจเมื่อ

computation required

Examples

risk estimation
data analysis
model simulation

Invocation workflow

Planner reasoning
 ↓
Tool invocation
 ↓
Tool result
 ↓
Planner interpretation
11. Agent Memory

Agent memory เก็บ

previous reasoning
tool results
critic feedback

Memory types

short-term context
structured reasoning outputs
tool outputs

Memory helps

maintain reasoning continuity
improve explanations
12. Agent Scaling Strategy

ระบบสามารถเพิ่ม agents ได้

Example scaling

2 agents → 5 agents → 10+ agents

Example configuration

Planner
Critic
Plant Pathology Agent
Climate Agent
Data Agent
Simulation Agent
13. Performance Considerations

Multi-agent systems มี challenge

context explosion
latency increase

Mitigation strategies

context summarization
specialized agents
hybrid model architecture

Example hybrid architecture

Planner → 7B model
Critic → smaller model
14. Example Research Workflow

Example system query

Explain rice blast infection risk under tropical climate

Workflow

Planner
 ↓
Rice blast model
 ↓
Tool output
 ↓
Critic review
 ↓
Refined explanation
15. Future Agent Capabilities

Planned capabilities

hypothesis generation
experimental design
model comparison
dataset analysis

System role

AI research collaborator
16. Long-Term Vision

Agent ecosystem จะ evolve เป็น

AI research laboratory

Capabilities

scientific reasoning
model analysis
hypothesis testing
experimental planning
📌 Summary

Agent system ถูกออกแบบให้ทำงานเหมือน

scientific research team

โดยมี

Planner
Critic
Domain Experts
Tool Agents

ที่ร่วมกันทำ

reason
analyze
simulate
critique

เพื่อสนับสนุน

AI-assisted scientific discovery
🚀 Next Step (สำคัญมาก)

ตอนนี้เอกสารของระบบคุณครบ ระดับ AI research project แล้ว

SYSTEM_ARCHITECTURE
SYSTEM_DIAGRAM
DEVELOPMENT_LOG
RESEARCH_SYSTEM_ROADMAP
TOOLS_LAYER_ARCHITECTURE
PROJECT_STRUCTURE
AGENT_DESIGN_SPEC

ขั้นต่อไปที่ผมแนะนำมากคือ

AGENT_PROMPT_LIBRARY.md

ซึ่งจะกำหนด

prompt ของ Planner
prompt ของ Critic
prompt ของ Domain Agents

และมันจะทำให้

agent reasoning ดีขึ้นมาก

เพราะ prompt engineering คือ สมองของ multi-agent system