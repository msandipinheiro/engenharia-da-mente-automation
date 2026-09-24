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

### Conteúdo avulso

Conteúdos fora da sequência usam `tipo: "avulso"`, `dia_calendario: null` e
um `id` estável. O nome do arquivo pode conter uma data sugerida, por exemplo
`queue/avulso-2026-09-18.json`; ao renomeá-lo, `data_publicacao` é atualizado
automaticamente quando o item é lido pelo pipeline.

```bash
python scripts/fila_aprovacao.py --listar
python scripts/gerar_midia.py --data educacao-preguica
python scripts/fila_aprovacao.py --aprovar educacao-preguica
python scripts/publicar_buffer.py --data educacao-preguica
```

Itens do calendário e avulsos com a mesma `data_publicacao` permanecem
permitidos, mas a aprovação e a publicação exibem um alerta de conflito.

## Multi-marca

Além da Engenharia da Mente (marca padrão), o pipeline atende outras marcas via
`--marca <slug>` em todos os scripts. Sem `--marca` (ou com
`--marca engenharia-da-mente`) nada muda em relação ao fluxo original.

| Marca | Slug | Config | Calendário | Fila | Canal Buffer |
|---|---|---|---|---|---|
| Engenharia da Mente | *(omitido)* | `config/brand.yaml` | `content/calendario-editorial.csv` | `queue/` | `BUFFER_CHANNEL_ID` |
| DivinoInconsciente | `divino-inconsciente` | `config/marcas/divino-inconsciente.yaml` | `content/divino-inconsciente/calendario-editorial.csv` | `queue/divino-inconsciente/` | `BUFFER_CHANNEL_ID_DIVINO_INCONSCIENTE` |
| ViverEmFluxo | `viver-em-fluxo` | `config/marcas/viver-em-fluxo.yaml` | `content/viver-em-fluxo/calendario-editorial.csv` | `queue/viver-em-fluxo/` | `BUFFER_CHANNEL_ID_VIVER_EM_FLUXO` |

```bash
# --data-ancora é obrigatório com --marca: é a data real do Dia 1 do calendário
python scripts/planejar_post.py --marca divino-inconsciente --dia 1 --data-ancora 2026-10-01
python scripts/gerar_midia.py --marca divino-inconsciente --data 2026-10-01
python scripts/fila_aprovacao.py --marca divino-inconsciente --listar
python scripts/fila_aprovacao.py --marca divino-inconsciente --aprovar 2026-10-01
python scripts/publicar_buffer.py --marca divino-inconsciente --data 2026-10-01
```

Para a Rota B, cada marca usa `IG_BUSINESS_ACCOUNT_ID_<MARCA>` (e, opcionalmente,
`META_ACCESS_TOKEN_<MARCA>`). Veja `.env.example`.

**Nova marca:** crie `config/marcas/<slug>.yaml` (mesmos campos das existentes,
incluindo `nome`, `handle`, `icone_marca` e `cores_slide`), o ícone em
`config/marcas/assets/` e `content/<slug>/calendario-editorial.csv` com as colunas
`Dia,Fase,Formato,Conteúdo,CTA`.

`cores_slide` define os papéis de cor dos carrosséis: `capa` (fundo da capa,
número e progresso), `fundo` (slides internos), `texto` (texto interno e @handle)
e `destaque` (etiqueta na capa).

**Mídia pública:** o Buffer e a Graph API baixam as imagens por
`PUBLIC_MEDIA_BASE_URL` + caminho em `midia`. Com raw.githubusercontent.com, as
imagens novas precisam estar commitadas e enviadas (push), e a base precisa apontar
para um commit (ou branch) que as contenha.

## Estrutura
```
config/            regras de marca, tom de voz, chaves de config (não versionar .env)
config/marcas/     uma config por marca adicional (+ assets/ com ícones e fotos de perfil)
content/           fonte do calendário editorial (content/<marca>/ nas marcas adicionais)
skills/             instruções de skill para o Claude Code usar em cada etapa
scripts/            código de fato
queue/              posts gerados aguardando aprovação (json); queue/<marca>/ nas marcas adicionais
.github/workflows/  exemplo de agendamento via GitHub Actions (opcional)
```

## Antes de rodar
```
cp .env.example .env   # preencha com suas chaves (Buffer OU Meta, nunca comitar)
pip install -r requirements.txt
```
