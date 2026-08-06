---
name: cockroachdb-agent-skills
description: CockroachDB Agent Skills for schema design, vector indexing, query optimization, and transaction retries in CockroachDB Cloud.
---

# CockroachDB Agent Skills Guide for RackPulse

This skill defines standard patterns and best practices for agents interacting with CockroachDB:

## 1. Vector Indexing Best Practices
- Always create native vector columns using `VECTOR(1024)`:
  ```sql
  ALTER TABLE memory_embeddings ADD COLUMN IF NOT EXISTS vector_native VECTOR(1024);
  CREATE VECTOR INDEX IF NOT EXISTS memory_embeddings_vector_idx ON memory_embeddings(vector_native);
  ```
- Use cosine distance operator `<=>` for similarity searches:
  ```sql
  SELECT id, summary, 1 - (vector_native <=> CAST(:vec AS VECTOR)) AS similarity
  FROM memory_embeddings
  WHERE vector_native IS NOT NULL
  ORDER BY vector_native <=> CAST(:vec AS VECTOR)
  LIMIT :k;
  ```

## 2. Hybrid Vector + Structured Search
- Combine vector distance ordering with structured SQL filters to narrow candidate sets:
  ```sql
  SELECT m.id, m.summary, 1 - (m.vector_native <=> CAST(:vec AS VECTOR)) AS similarity
  FROM memory_embeddings m
  WHERE m.vector_native IS NOT NULL
    AND m.memory_type = :mtype
    AND m.created_at >= NOW() - INTERVAL '24 hours'
  ORDER BY m.vector_native <=> CAST(:vec AS VECTOR)
  LIMIT :k;
  ```

## 3. Transaction Retry Logic
- Always catch `SerializationFailure` errors in multi-statement transactions and retry using exponential backoff.

## 4. ccloud CLI Cluster Monitoring
- Check cluster health before executing heavy database migrations or writes using `ccloud cluster inspect <cluster_id> --format json`.
