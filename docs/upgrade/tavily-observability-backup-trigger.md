# Tavily Observability Backup Trigger

CareerVP should add a secondary search provider only after production metrics show sustained Tavily instability. The trigger is either sustained `TavilySearchFailure` above 5% for one hour or repeated Tavily quota or credit exhaustion errors that cause `CompanyResearchAllSourcesFailed`.

Until one of those conditions is met, a second search provider is premature operational complexity.
