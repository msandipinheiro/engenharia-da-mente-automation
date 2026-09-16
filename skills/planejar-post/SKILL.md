---
name: planejar-post
description: Lê o dia do calendário editorial e gera o rascunho de copy/legenda no tom de voz da marca Engenharia da Mente / Mente Sob Medida. Use antes de gerar mídia ou publicar.
---

# Planejar Post

1. Leia `config/brand.yaml` (tom de voz, disclaimers, público) e
   `content/calendario-editorial.csv` (linha do dia solicitado).
2. Gere a legenda seguindo estritamente o tom de voz — nunca capacitista,
   nunca promete cura, sem jargão clínico não explicado.
3. Se a fase do dia for "Aquecimento" ou "Pré-lançamento", NÃO use a palavra
   TDAH de forma que exija autoidentificação do leitor (ver regra de topo
   de funil em brand.yaml).
4. Se o conteúdo envolver o autoteste, inclua o disclaimer obrigatório.
5. Devolva: {legenda, cta, hashtags_sugeridas, alerta_se_fora_do_tom}.
6. NÃO publique nada nesta etapa — apenas grave o rascunho em
   `queue/<data>.json` com status "rascunho".
