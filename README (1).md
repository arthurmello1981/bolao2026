# Bolão Copa do Mundo 2026

Painel do bolão que se atualiza sozinho: uma GitHub Action busca os placares no
[openfootball](https://github.com/openfootball/worldcup.json) (domínio público, sem
chave de API) e grava `results.json`; a página lê esse arquivo e recalcula o ranking.

## Arquivos

- `index.html` — o painel (ranking, placares, chaveamento, participantes, stats, análise, regras)
- `results.json` — placares da fase de grupos, gerado pela automação: `{ "num_do_jogo": [golsA, golsB] }`
- `scripts/fetch_results.py` — busca no openfootball e traduz os nomes pra numeração do bolão
- `.github/workflows/update-results.yml` — roda o script de hora em hora e commita se mudou

## Como ligar (uma vez só)

1. Suba esses arquivos num repositório **público**.
2. **Settings → Pages → Source: `Deploy from a branch` → `main` / `(root)`** → Save.
   Em ~1 min a página fica no ar em `https://SEU_USUARIO.github.io/NOME_DO_REPO/`.
3. **Settings → Actions → General → Workflow permissions → `Read and write`** → Save.
   (Sem isso a Action não consegue commitar o `results.json`.)
4. **Aba Actions → "Atualizar placares" → Run workflow** pra rodar a primeira vez na hora
   (o cron sozinho roda no próximo horário cheio).

Pronto. A partir daí a página mostra sempre o ranking atualizado, sem você digitar nada.

## Edição manual continua valendo

A automação preenche tudo, mas **qualquer placar que você digitar à mão na aba
"Placares Oficiais" vence** o automático — porém isso fica salvo só no SEU navegador
(localStorage) e vale só na sua tela. Use como conferência rápida pra você.

Ordem na tela: `automático (results.json)` < `sua edição manual (localStorage, só local)`.

## Corrigir um placar PARA TODO MUNDO (modo juiz)

Quando o openfootball estiver errado ou atrasado e você quiser corrigir pra geral,
edite o bloco `OVERRIDES` no topo de `scripts/fetch_results.py`:

```python
OVERRIDES = {
    17: [2, 1],   # jogo 17 (Haiti x Brasil) — openfootball estava errado
}
```

Suas correções **vencem o openfootball** e são reaplicadas toda vez que o robô roda —
então não tem risco de ele desfazer. Commite a mudança (ou me peça) e na próxima rodada
o `results.json` já sai corrigido pra todo o grupo. Quando o openfootball arrumar a fonte,
apague a linha do `OVERRIDES`.


## Limitações conhecidas

- **Só fase de grupos por enquanto.** O mata-mata (jogos 73–104) só pontua depois que os
  classificados forem fixados no `MATCHES` do HTML — aí dá pra estender o script.
- **Depende do openfootball.** É mantido por voluntários; um placar pode atrasar algumas
  horas. Se atrasar, digita na mão (vide acima).
- **Se um nome de seleção não casar** (ex: o openfootball renomear "Turkey" pra "Türkiye"),
  o script avisa no log da Action qual nome não reconheceu — é só adicionar o apelido no
  dicionário `ALIASES` em `scripts/fetch_results.py`.

## Rodar o script localmente

```bash
python scripts/fetch_results.py   # grava results.json na pasta atual
```
