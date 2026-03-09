## Summary          
                      
Phase 1/3 of the Telegram Bot integration. This PR adds the base infrastructure namespace (`bots/telegram/`) to support future bot handlers.

It does **not** introduce any runtime logic or Telegram dependencies yet. It sets up `uv` dependency management, linting (`ruff`), typing (`mypy`), an empty test suite, and the Docker compile target so the CI can validate the foundation.
                      
## Scope (Infra only) 
                      
 Action │ File      
────────┼─────────  
 NEW    │ bots/telegram/src/bracc_telegram/config.py
 NEW    │ bots/telegram/Dockerfile
 NEW    │ bots/telegram/pyproject.toml
 MODIFY │ docker-compose.yml
 MODIFY │ Makefile
                      
## Change type      
                      
[x] `release:infra`
                      
## Breaking change? 
                      
[x] No              
                      
## Validation       
                      
[x] Local tests/checks passed for impacted scope (ruff, mypy, pytest)
[x] CI and Security checks are green    
[x] Exactly one release label is set on this PR          
                      
## Public safety and compliance checklist
                      
[x] No personal identifier exposure was introduced      
[x] `PUBLIC_MODE` behavior was reviewed (if relevant)           
[x] Public boundary gate is green       
[x] Public endpoints and demo data contain no personal data fields
[x] Legal/policy docs were reviewed for scope-impacting changes             
[x] Snapshot boundary remains compliant with docs
                      
## Risk and rollback
                      
Zero runtime risk. Empty infrastructure shell. Rollback by reverting.
