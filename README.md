# AI Daily Digest for GitHub Pages

Projeto simples para gerar uma newsletter diária de IA com:
- papers recentes do arXiv
- resultados reais do Google Acadêmico via SerpAPI quando configurado
- fallback para pesquisas acadêmicas recentes via Crossref quando a SerpAPI não estiver configurada
- notícias recentes via Google News RSS
- artigos e blogs de empresas de IA
- site estático publicado no GitHub Pages
- envio opcional por e-mail via Resend

## Como publicar

1. Crie um repositório novo no GitHub.
2. Envie todos os arquivos deste projeto.
3. No GitHub, vá em **Settings > Pages** e deixe a publicação por **GitHub Actions**.
4. Rode o workflow manualmente em **Actions > Daily AI Digest > Run workflow**.

## Horário

O workflow roda diariamente no cron `0 10 * * *`.
No GitHub Actions, o cron é em UTC. Isso equivale a **07:00 no horário de Brasília** quando o Brasil está em UTC-3.

## E-mail opcional

Se quiser receber no e-mail, adicione estes secrets no repositório:
- `RESEND_API_KEY`
- `NEWSLETTER_TO`
- `NEWSLETTER_FROM` (opcional)

## Google Acadêmico via SerpAPI

Para ativar resultados reais do Google Acadêmico, adicione este secret no repositório:
- `SERPAPI_API_KEY`

Sem esse secret, a seção acadêmica continua funcionando com fallback da Crossref.

## Limitações deste MVP

- LinkedIn não foi integrado automaticamente porque scraping de posts é instável, depende de autenticação e pode exigir ferramentas externas.
- Google Acadêmico não tem um feed público estável para rodar isso todo dia via GitHub Actions. Por isso, a integração real depende da SerpAPI; sem a chave, a seção acadêmica usa Crossref como fallback.
- Para ampliar fontes, adicione mais feeds RSS em `scripts/fetch_sources.py`.

## Estrutura

- `site/` site estático
- `scripts/fetch_sources.py` coleta dados
- `scripts/send_email.py` envia newsletter por e-mail
- `.github/workflows/daily-digest.yml` agenda diária e deploy
