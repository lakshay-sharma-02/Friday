# Phase 10 Architecture Diagram

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAPABILITY LAYER                                 │
│                    (Unified Entry Point)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAPABILITY ROUTER                                 │
│                                                                           │
│  • Semantic keyword matching                                             │
│  • Scoring: keywords (40%) + category (20%) + latency (20%) +           │
│             complexity (20%)                                             │
│  • Returns: Capability + Execution Strategy                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌──────────────────────┐      ┌──────────────────────┐
        │  Capability Metadata │      │  Execution Strategy  │
        ├──────────────────────┤      ├──────────────────────┤
        │ • Name               │      │ • direct             │
        │ • Category           │      │ • tool_direct        │
        │ • Owner              │      │ • pipeline           │
        │ • Requirements       │      │ • llm                │
        │ • Latency            │      └──────────────────────┘
        │ • Keywords           │
        └──────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       CAPABILITY EXECUTOR                                │
│                (Delegates to Owning Subsystems)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────┬───────────┴───────────┬───────────┬──────────────┐
        │               │                       │           │              │
        ▼               ▼                       ▼           ▼              ▼
   ┌─────────┐   ┌──────────┐          ┌──────────┐  ┌─────────┐   ┌──────────┐
   │ System  │   │Workspace │          │   Git    │  │ Memory  │   │Filesystem│
   │  State  │   │ Context  │          │  State   │  │ Recall  │   │  Ops     │
   └─────────┘   └──────────┘          └──────────┘  └─────────┘   └──────────┘
        │               │                     │            │              │
        ▼               ▼                     ▼            ▼              ▼
   ┌─────────┐   ┌──────────┐          ┌──────────┐  ┌─────────┐   ┌──────────┐
   │ World   │   │ Project  │          │ World    │  │ Memory  │   │ Pipeline │
   │ State   │   │ Context  │          │ State    │  │ Manager │   │    →     │
   │         │   │          │          │          │  │         │   │ Executor │
   └─────────┘   └──────────┘          └──────────┘  └─────────┘   └──────────┘
        │               │                     │            │              │
        ▼               ▼                     ▼            ▼              ▼
   Observers      Workspace              Workspace     search()     File Tools
   (instant)      Observer               Observer      (fast)       (moderate)
                  (instant)              (instant)
