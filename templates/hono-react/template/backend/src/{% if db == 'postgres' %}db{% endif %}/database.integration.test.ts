import postgres from 'postgres'
import { afterAll, describe, expect, it } from 'vitest'

// Proves the integration lane has a REAL, PRIVATE database.
//
// The second assertion is the one that matters for parallel work: the database this test
// talks to is not the checkout's dev database, so two worktrees running `mise run
// test:integration` at the same time cannot drop or migrate each other's data. When this
// file was written that was the single most common way a parallel batch failed — and it
// never looked like a collision, it looked like the code was broken.
const url = process.env.DATABASE_URL
if (!url) throw new Error('DATABASE_URL not set — run via `mise run test:integration`')

const sql = postgres(url, { max: 1 })

afterAll(async () => {
  await sql.end()
})

describe('integration database', () => {
  it('accepts connections and is a real postgres', async () => {
    const [row] = await sql`select current_database() as db, 1 as ok`
    expect(row.ok).toBe(1)
    expect(typeof row.db).toBe('string')
  })

  it('is NOT this checkout\'s dev database', async () => {
    const [row] = await sql`select current_database() as db`
    // WF_DB_NAME is the dev database mise derived for this checkout. Testcontainers gave
    // us a different one; if these ever match, the lane is pointing at long-lived data.
    if (process.env.WF_DB_NAME) {
      expect(row.db).not.toBe(process.env.WF_DB_NAME)
    }
  })
})
