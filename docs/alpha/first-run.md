# First-run Checklist

Use this checklist after a fresh clone.

| Step | Command or doc | Expected success |
| --- | --- | --- |
| 1. Install Alice | `make setup` | `.venv` and web dependencies exist |
| 2. Run migrations | `make migrate` | Postgres is up and Alembic reaches head |
| 3. Run doctor | `make doctor` | no blocking failures |
| 4. Start API | `APP_RELOAD=false ./scripts/api_dev.sh` | API serves locally |
| 5. Start scheduler | `alicebot vnext scheduler daemon start --foreground` | daemon reports status and due scans |
| 6. Start `/vnext` | `pnpm --dir apps/web dev` | web app serves locally |
| 7. Open `/vnext` | `http://localhost:3000/vnext` | live mode loads or shows a clear empty state |
| 8. Configure Brain Charter | [../vnext/ALICE.example.md](../vnext/ALICE.example.md) | Brain Charter is visible in Settings |
| 9. Configure one capture path | local folder, browser clipper, or Telegram | connector health becomes configured |
| 10. Capture first source | `alicebot vnext sources capture-text "Fact: first alpha source" --domain project --sensitivity private` | source appears in Inbox |
| 11. Review captured source | `/vnext` Inbox | review event appears in Timeline |
| 12. Generate artifact | `alicebot daily-brief --generate --domain project` | artifact appears in Generated |
| 13. Review or rate artifact | `/vnext` Generated | rating appears in dogfooding telemetry |
| 14. Inspect trace | `/vnext` Trace | source, chunks, memories, artifacts, and events link together |
| 15. Connect an agent | [agent-integration.md](agent-integration.md) | context pack, output ingestion, and proposal flow works |

When doctor fails, go to [doctor.md](doctor.md) first. It lists the exact command that usually fixes the blocking issue.
