## Architecture decisions

- [0001] Keep full, trigger-phrase-rich descriptions on the five stack skills — shrinking a description to a one-liner deletes exactly the text routing depends on, because the body isn't read until after selection, and this repo has no eval suite to catch the resulting mis-routing: hono-ts-backend, kotlin-springboot, react-ts-vite, pulumi-gcp-ts, mise keep their full trigger phrases + disambiguation clauses, ratcheted by `wellforge-plugin/config/budget.yml` (see docs/adr/0001-keep-full-stack-skill-descriptions.md)
