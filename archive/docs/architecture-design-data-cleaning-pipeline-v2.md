# Next-Gen Spatial Data Cleaning Pipeline Architecture (v2.0)

**Version**: 2.0 (Draft)
**Date**: 2026-02-16
**Status**: Proposed
**Author**: System Architect Agent

## 1. Background & Objectives

The current data cleaning implementation (`AddressGovernanceSystem`) is tightly coupled, in-memory, and relies heavily on hardcoded regex rules. To support the "Spatial Intelligence Data Factory" vision, we need a scalable, observable, and intelligent pipeline.

**Objectives:**
- **Decoupling**: Separate cleaning logic (rules) from execution engine.
- **Scalability**: Support batch processing of millions of address records.
- **Intelligence**: Integrate LLM capabilities for handling ambiguous or unstructured addresses where regex fails.
- **Observability**: detailed metrics on data quality pass rates and lineage.

## 2. High-Level Architecture

The new architecture adopts a **Lakehouse** pattern with a **Hybrid Processing Engine**.

```mermaid
graph TD
    subgraph "Ingestion Layer"
        Src_API[API Sources] --> Kafka
        Src_File[File/Batch] --> S3_Bronze[(Bronze: Raw Data)]
    end

    subgraph "Processing Layer (The Engine)"
        direction TB
        
        Bronze_Read[Reader] --> Pre_Process[Pre-processing\n(Normalization)]
        
        subgraph "Cleaning Strategy Router"
            Pre_Process --> Router{Complexity Check}
            Router -- "Simple/Standard" --> Rule_Engine[Rule Engine\n(Regex/Lookup)]
            Router -- "Complex/Ambiguous" --> LLM_Engine[LLM Agent\n(Semantic Parsing)]
        end
        
        Rule_Engine --> Merger[Result Merger]
        LLM_Engine --> Merger
        
        Merger --> Validator[Quality Validator\n(Great Expectations)]
    end

    subgraph "Storage Layer"
        Validator -- "Valid" --> Silver[(Silver: Cleansed)]
        Validator -- "Invalid" --> Quarantine[(Quarantine: Failed)]
        
        Silver --> Entity_Res[Entity Resolution\n(Dedup & Link)]
        Entity_Res --> Gold[(Gold: Spatial Graph)]
    end

    subgraph "Control Plane"
        Config[Rule Config / Metadata] -.-> Rule_Engine
        Monitor[Observability Dashboard] -.-> Validator
    end
```

## 3. Core Modules

### 3.1 Ingestion Layer
- **Responsibility**: Standardize input formats (JSON, CSV, API) into a unified internal schema.
- **Storage**: **Bronze Layer** (Raw), immutable history of inputs.

### 3.2 Hybrid Cleaning Engine
This is the core innovation, combining speed and intelligence.

*   **Fast Path (Rule Engine)**:
    *   **Tech**: Python (Pandas/Polars) or SQL (dbt).
    *   **Logic**: Deterministic regex, dictionary lookups (e.g., `SHANGHAI_DISTRICTS`).
    *   **Use Case**: 80% of standard addresses.
    *   **Config**: Rules stored in YAML/Database, not code.

*   **Smart Path (LLM Engine)**:
    *   **Tech**: LangChain / LiteLLM.
    *   **Logic**: Few-shot prompting to parse non-standard addresses (e.g., "The coffee shop opposite to Joy City").
    *   **Use Case**: 20% of tail cases where rules fail.

### 3.3 Quality Validator
- **Framework**: Great Expectations or Pandera.
- **Checks**:
    - Completeness (Mandatory fields present).
    - Consistency (Province/City match).
    - Validity (Geo-coordinates within bounds).

### 3.4 Storage Layer (Data Lakehouse)
- **Bronze**: Raw ingestion (JSON/Parquet).
- **Silver**: Cleaned, standardized, schema-enforced (Parquet/Iceberg).
- **Gold**: Business-level aggregates, Knowledge Graph (Neo4j/NetworkX).
- **Quarantine**: Bad data for manual review.

## 4. Implementation Roadmap

### Phase 1: Refactoring (Current -> v1.5)
- Extract regex rules from `AddressParser` into a configuration file (`config/rules/address_regex.yaml`).
- Implement `Quarantine` bucket for failed parse results instead of discarding them.

### Phase 2: Hybrid Engine (v2.0)
- Integrate an LLM fallback mechanism for addresses with low confidence scores (< 0.6).
- Implement the "Router" logic to dispatch tasks.

### Phase 3: Scale & Graph
- Migrate processing to a distributed framework (if data volume > 1GB).
- Build the "Gold" layer with persistent Graph Database integration.
