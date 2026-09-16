---
name: gerar-midia
description: Gera a imagem ou carrossel de um post seguindo a paleta e tipografia da marca, e sobe para um local com URL pública (necessário para publicação via API). Use depois de planejar-post.
---

# Gerar Mídia

1. Use `config/brand.yaml` para cores/fontes.
2. Gere a imagem (matplotlib/PIL, como os diagramas do material principal)
   ou o carrossel (uma imagem por slide).
3. Salve em `queue/media/<data>-<n>.png`.
4. Se for usar a Rota B (Graph API), a mídia PRECISA estar acessível por
   URL pública no momento da publicação — suba para o bucket configurado
   em `PUBLIC_MEDIA_BASE_URL` antes de marcar o post como pronto.
   Se for usar a Rota A (Buffer), a própria API do Buffer aceita upload
   direto — não precisa de URL pública.
5. Atualize `queue/<data>.json` com o(s) caminho(s) da mídia e status
   "pronto_para_aprovacao".
