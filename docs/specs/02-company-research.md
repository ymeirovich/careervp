# Spec: Company Research (Option D - Hybrid)
## Logic
1. Use an MCP tool (like `google-search` or `brave-search`) to find the latest company "About" page and recent news.
2. Scrape the text and use Sonnet 4.5 to extract:
   - Core Values/Mission
   - Current Strategic Priorities
   - Recent Financial Performance (if public)
3. Output a `CompanyContext` JSON object for the VPR Generator.
## Constraint
Budget: < $0.01 per company. If scraping fails, fallback to a "General Industry Knowledge" prompt.
