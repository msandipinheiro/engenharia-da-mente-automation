# Engenharia da Mente — Automação de Publicação

Repositório para orquestrar, via Claude Code, a produção e publicação de
conteúdo do perfil **@engenhariadamente.oficial** (marca guarda-chuva de
Marcello, cujo primeiro produto é o Mente Sob Medida).

Este repositório é DELIBERADAMENTE separado do Project de conteúdo/estratégia
no claude.ai — aqui vivem credenciais, agendamento e código de produção.

## Duas rotas de publicação (escolha uma para começar)

### Rota A — Buffer (recomendada para começar)
- Plano Free do Buffer inclui acesso à API, 3 canais, 10 posts agendáveis
  por canal (renováveis). Suficiente para validar a cadência de ~4-5
  posts/semana no feed antes de qualquer investimento.
- Se o volume exceder o Free: plano Essentials ≈ US$ 5–6/canal/mês.
- Sem App Review da Meta, sem Facebook Page vinculada, sem espera de
  aprovação — é o caminho de menor atrito técnico e financeiro.
- Ver `scripts/publicar_buffer.py`.

### Rota B — Instagram Graph API (Meta) direto
- Exige: conta Instagram Business/Creator vinculada a uma Página do
  Facebook, App registrado no Meta for Developers, App Review aprovado
  (2-5 dias úteis), mídia hospedada em URL pública no momento da publicação.
- Sem custo de plataforma, mas custo de engenharia maior e dependência de
  aprovação externa (Meta).
- Ver `scripts/publicar_graph_api.py`.

**Sugestão:** comece pela Rota A para validar o ritmo de publicação; migre
para a Rota B só se precisar de volume/controle que o Buffer não ofereça.

## Fluxo com aprovação humana (recomendado nos primeiros meses)
1. `scripts/planejar_post.py` lê `content/calendario-editorial.csv` e gera
   o rascunho de copy do dia (usa a Claude API).
2. `scripts/gerar_midia.py` gera a imagem/carrossel no padrão visual da
   marca (paleta teal, ver `config/brand.yaml`) e salva em `queue/`.
3. O rascunho + mídia ficam em `queue/AAAA-MM-DD.json` até você aprovar
   (`scripts/fila_aprovacao.py --listar` / `--aprovar <data>`).
4. Só então `scripts/publicar_buffer.py` (ou `publicar_graph_api.py`)
   envia o post aprovado.

## Estrutura
```
config/            regras de marca, tom de voz, chaves de config (não versionar .env)
content/           fonte do calendário editorial
skills/             instruções de skill para o Claude Code usar em cada etapa
scripts/            código de fato
queue/              posts gerados aguardando aprovação (json)
.github/workflows/  exemplo de agendamento via GitHub Actions (opcional)
```

## Antes de rodar
```
cp .env.example .env   # preencha com suas chaves (Buffer OU Meta, nunca comitar)
pip install -r requirements.txt
```
