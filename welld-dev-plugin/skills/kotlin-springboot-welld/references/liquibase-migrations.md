# Liquibase Migrations Reference

All schema changes go through Liquibase SQL changesets.  
**Never use XML or YAML changeset format** — SQL only.

---

## Directory Layout

```
src/main/resources/db/changelog/
├── db.changelog-master.yaml          ← master file, lists all changes
└── changes/
    ├── 001-create-users-postgres.sql
    ├── 001-create-users-h2.sql
    ├── 002-add-orders-postgres.sql
    ├── 002-add-orders-h2.sql
    └── ...
```

---

## Master Changelog

```yaml
# db.changelog-master.yaml
databaseChangeLog:
  - includeAll:
      path: changes/
      relativeToChangelogFile: true
```

Using `includeAll` loads all `.sql` files in alphabetical order.  
Files are picked up by Liquibase's `dbms` attribute automatically — at runtime only the  
Postgres changesets execute; at codegen time only the H2 changesets execute.

---

## When to Split (Dual DBMS Pattern)

Create **two** migration files whenever your SQL uses Postgres-specific syntax:

| Postgres feature | H2 alternative |
|---|---|
| `BIGSERIAL` / `SERIAL` | `BIGINT AUTO_INCREMENT` |
| `TEXT` | `VARCHAR(n)` or `CLOB` |
| `jsonb` / `json` | `JSON` (limited) or `CLOB` |
| `UUID` with `gen_random_uuid()` | `UUID DEFAULT RANDOM_UUID()` |
| `ON CONFLICT DO UPDATE` | not supported — omit for H2 file |
| Postgres enums (`CREATE TYPE`) | use `VARCHAR` in H2 |
| `BOOLEAN` default `true/false` | same but write `TRUE`/`FALSE` uppercase |

If the SQL is identical for both DBMS, you may use a **single file** with no `dbms` attribute  
(Liquibase runs it everywhere). Only split when necessary.

---

## File Naming Convention

```
{NNN}-{description}-postgres.sql    ← production changeset
{NNN}-{description}-h2.sql          ← codegen-only changeset
```

Both files carry the **same changeset ID** (the `--changeset` line). The `dbms` attribute ensures  
only one runs per environment.

---

## Changeset Format — Postgres

```sql
--liquibase formatted sql
--changeset yourname:001-create-users dbms:postgresql

CREATE TABLE users (
    id         BIGSERIAL PRIMARY KEY,
    email      TEXT NOT NULL,
    full_name  TEXT,
    active     BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_email UNIQUE (email)
);

--rollback DROP TABLE users;
```

## Changeset Format — H2 (codegen only)

```sql
--liquibase formatted sql
--changeset yourname:001-create-users dbms:h2

CREATE TABLE users (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    full_name  VARCHAR(255),
    active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_email UNIQUE (email)
);

--rollback DROP TABLE users;
```

---

## Postgres-Specific Example — JSONB Column

```sql
--liquibase formatted sql
--changeset yourname:003-add-metadata-to-orders dbms:postgresql

ALTER TABLE orders ADD COLUMN metadata JSONB;
```

```sql
--liquibase formatted sql
--changeset yourname:003-add-metadata-to-orders dbms:h2

ALTER TABLE orders ADD COLUMN metadata CLOB;
```

---

## Postgres-Specific Example — Enum Type

```sql
--liquibase formatted sql
--changeset yourname:004-create-status-enum dbms:postgresql

CREATE TYPE order_status AS ENUM ('PENDING', 'PROCESSING', 'DONE', 'CANCELLED');

ALTER TABLE orders ADD COLUMN status order_status NOT NULL DEFAULT 'PENDING';
```

```sql
--liquibase formatted sql
--changeset yourname:004-create-status-enum dbms:h2

ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDING';
```

---

## Contexts

Use contexts to control which changesets run in which scenario:

| Context | Purpose |
|---|---|
| *(none)* | Always runs |
| `test` | Test data / fixtures only |
| `generate_skip` | Skip during jOOQ codegen (complex Postgres DDL that can't be mapped to H2) |

Example — test fixture skipped in codegen:

```sql
--liquibase formatted sql
--changeset yourname:T001-seed-test-users dbms:postgresql context:test

INSERT INTO users (email, full_name) VALUES ('test@welld.ch', 'Test User');
```

The jooq-codegen-maven plugin is configured with:
```
changeLogParameters.contexts = !test,!generate_skip
```
so test and generate_skip changesets are excluded from record generation.

---

## application.yml — Liquibase config

```yaml
spring:
  liquibase:
    change-log: classpath:/db/changelog/db.changelog-master.yaml
    enabled: true
```

For tests with Testcontainers, Liquibase runs automatically against the real Postgres container.

---

## Common Mistakes to Avoid

- ❌ Do NOT add `dbms:h2` changesets to a file also containing `dbms:postgresql` changesets.  
  Keep them in separate files for clarity.
- ❌ Do NOT write Postgres changesets that reference H2 limitations.
- ❌ Do NOT use `--rollback DROP TABLE` in destructive production migrations without careful review.
- ✅ Always provide a `--rollback` statement.
- ✅ Always include `NOT NULL` or a default — avoid nullable columns unless the business domain requires it.
- ✅ Use `TIMESTAMPTZ` (not `TIMESTAMP`) for all timestamps in Postgres files.
