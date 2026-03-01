# AI PR Governor (Claude Code)

Fluxo conservador para review, aprovação e auto-merge de PRs internas no `main`.

## Objetivo

- Avaliar PRs com Claude Code (`claude-opus-4-6`) usando saída estruturada.
- Aplicar política determinística (`scripts/claude_merge_gate.py`) antes de qualquer merge.
- Aprovar formalmente e fazer squash merge só quando todos os gates passarem.
- Registrar auditoria em Linear para toda decisão.

## Arquivos principais

- Workflow: `.github/workflows/claude-pr-governor.yml`
- Política: `.github/claude-automerge-policy.json`
- Scanner de injeção: `scripts/prompt_injection_scan.py`
- Gate determinístico: `scripts/claude_merge_gate.py`
- Auditoria Linear: `scripts/linear_audit.py`

## Pré-requisitos

### Secrets

1. `CLAUDE_CODE_OAUTH_TOKEN`
   - Gere localmente via `claude setup-token` com sua conta Max.
2. `LINEAR_API_KEY`

### Variables

1. `LINEAR_TEAM_ID`
2. `CLAUDE_AUTOMERGE_ENABLED`
   - `false` para shadow mode
   - `true` para ativar merge automático
3. `CLAUDE_AUTOFIX_ENABLED`
   - recomendado: `true`

### GitHub Actions setting obrigatório

No repositório, habilite:

- **Actions can approve pull request reviews** = `true`

Sem isso, o passo `gh pr review --approve` pode falhar.

## Comportamento do fluxo

1. **Preflight**
   - bloqueia forks
   - roda scanner de prompt injection
   - aplica allowlist/denylist e thresholds de churn
2. **Claude evaluation**
   - exige schema com campos: `useful`, `necessary`, `safe`, `confidence`, `risk_level`, `blocking_findings`, `summary`
3. **Required checks gate**
   - espera checks obrigatórios até timeout (45 min por padrão)
   - se falhar, tenta auto-fix 1x apenas para checks técnicos elegíveis
4. **Approve + merge**
   - só com kill switch ativo (`CLAUDE_AUTOMERGE_ENABLED=true`)
   - aprovação formal + squash merge
5. **Linear audit**
   - cria issue em toda decisão
   - fallback para comentário em PR se Linear falhar

## Kill switch e rollback

### Kill switch imediato

Defina:

- `CLAUDE_AUTOMERGE_ENABLED=false`

O workflow continua auditando/comentando, mas não faz merge.

### Rollback total

1. Desabilitar workflow `Claude PR Governor` no GitHub Actions.
2. Reverter o arquivo `.github/workflows/claude-pr-governor.yml`.

## Troubleshooting

### Não aprovou PR

- Verifique se `can_approve_pull_request_reviews` está habilitado no repo.
- Verifique permissões do `GITHUB_TOKEN` no workflow.

### Não fez merge

- Confirme `CLAUDE_AUTOMERGE_ENABLED=true`.
- Revise comentário final no PR e `decision` calculada.
- Verifique se houve novo commit concorrente.

### Auditoria Linear falhou

- Verifique `LINEAR_API_KEY` e `LINEAR_TEAM_ID`.
- O merge não é bloqueado por falha de auditoria; há fallback em comentário de PR.

## Rollout recomendado

1. **Fase Shadow (3-5 dias)**
   - `CLAUDE_AUTOMERGE_ENABLED=false`
2. **Ativação controlada**
   - ligar kill switch (`true`) mantendo política conservadora
3. **Ajuste fino**
   - calibrar allowlist/denylist e thresholds conforme dados reais
