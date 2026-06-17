# HLD — High Level Design

This folder contains all high-level design artifacts for ContextOS.

## Contents

| File | Description |
|---|---|
| [system-overview.md](system-overview.md) | System purpose, positioning, and the five core concepts |
| [architecture-diagram.md](architecture-diagram.md) | Full ASCII architecture diagrams + component relationships |
| [data-flow.md](data-flow.md) | End-to-end request flow through all system layers |
| [tech-stack-rationale.md](tech-stack-rationale.md) | Why each technology was chosen |

## The One-Line Summary

ContextOS is a context optimization layer that sits between a user and any LLM, maximizing answer quality per token by scoring, pruning, compressing, and validating context before inference.

## Source of Truth

The primary HLD document is `ContextOS_HLD_v2.md` at the repository root. Files here are complementary breakdowns and diagrams.
