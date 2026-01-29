# careervp
This is a great README file by yitzchak meirovich (ymeirovich@presgen.net)


The service is about:
dev for careervp

# careervp

## API contract verification

- The PR CI workflow only runs the OpenAPI compare step when the stack is successfully deployed, guaranteeing it validates against live AWS state.
- A daily “OpenAPI Drift Check” (see `.github/workflows/openapi-drift.yml`) re-downloads the swagger from the deployed API and compares it to `docs/swagger/openapi.json`. Trigger it manually after large changes if you need an immediate confirmation.
