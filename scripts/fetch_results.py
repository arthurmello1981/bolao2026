#!/usr/bin/env python3
"""
Busca os placares da fase de grupos da Copa 2026 no openfootball (domínio público,
sem chave de API) e grava results.json no formato do bolão: { "num_do_jogo": [golsA, golsB] }.

- Casa cada jogo pelo PAR de seleções (independe da ordem em que o openfootball lista),
  e orienta o placar conforme a ordem A/B oficial do bolão.
- Nomes não reconhecidos são reportados no log (não quebram a execução) — basta
  adicionar o apelido em ALIASES e rodar de novo.
- Pênaltis: usa só o placar do tempo normal/prorrogação (campo "ft"), nunca o agregado.

Só fase de grupos por enquanto. Mata-mata depende dos classificados serem fixados
no HTML primeiro (jogos 73-104).
"""
import json
import sys
import unicodedata
import urllib.request

SOURCE = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# Grupos na MESMA ordem do HTML (define a numeração 1-72).
GROUPS = {
    'A': ['México', 'África do Sul', 'Coreia do Sul', 'Rep. Tcheca'],
    'B': ['Canadá', 'Bósnia', 'Catar', 'Suíça'],
    'C': ['Brasil', 'Marrocos', 'Escócia', 'Haiti'],
    'D': ['Estados Unidos', 'Turquia', 'Paraguai', 'Austrália'],
    'E': ['Alemanha', 'Curaçao', 'Costa do Marfim', 'Equador'],
    'F': ['Holanda', 'Japão', 'Suécia', 'Tunísia'],
    'G': ['Bélgica', 'Egito', 'Irã', 'Nova Zelândia'],
    'H': ['Espanha', 'Cabo Verde', 'Uruguai', 'Arábia Saudita'],
    'I': ['França', 'Iraque', 'Noruega', 'Senegal'],
    'J': ['Argentina', 'Áustria', 'Argélia', 'Jordânia'],
    'K': ['Portugal', 'Uzbequistão', 'Colômbia', 'RD Congo'],
    'L': ['Inglaterra', 'Croácia', 'Gana', 'Panamá'],
}

# Ordem dos confrontos dentro de cada grupo (índices dos times). Igual ao HTML:
# jogo1: t1xt2, jogo2: t3xt4, jogo3: t1xt3, jogo4: t4xt2, jogo5: t4xt1, jogo6: t2xt3
PAIRS = [(0, 1), (2, 3), (0, 2), (3, 1), (3, 0), (1, 2)]

# openfootball usa nomes em inglês. Aliases generosos cobrindo variantes comuns.
# Chave = nome normalizado (sem acento, minúsculo). Valor = nome canônico do bolão.
ALIASES = {
    'mexico': 'México',
    'south africa': 'África do Sul',
    'south korea': 'Coreia do Sul', 'korea republic': 'Coreia do Sul', 'korea south': 'Coreia do Sul',
    'czech republic': 'Rep. Tcheca', 'czechia': 'Rep. Tcheca',
    'canada': 'Canadá',
    'bosnia and herzegovina': 'Bósnia', 'bosnia-herzegovina': 'Bósnia', 'bosnia herzegovina': 'Bósnia', 'bosnia': 'Bósnia',
    'qatar': 'Catar',
    'switzerland': 'Suíça',
    'brazil': 'Brasil',
    'morocco': 'Marrocos',
    'scotland': 'Escócia',
    'haiti': 'Haiti',
    'united states': 'Estados Unidos', 'usa': 'Estados Unidos', 'united states of america': 'Estados Unidos',
    'turkey': 'Turquia', 'turkiye': 'Turquia',
    'paraguay': 'Paraguai',
    'australia': 'Austrália',
    'germany': 'Alemanha',
    'curacao': 'Curaçao',
    'ivory coast': 'Costa do Marfim', 'cote d ivoire': 'Costa do Marfim', 'cote divoire': 'Costa do Marfim',
    'ecuador': 'Equador',
    'netherlands': 'Holanda', 'holland': 'Holanda',
    'japan': 'Japão',
    'sweden': 'Suécia',
    'tunisia': 'Tunísia',
    'belgium': 'Bélgica',
    'egypt': 'Egito',
    'iran': 'Irã', 'ir iran': 'Irã',
    'new zealand': 'Nova Zelândia',
    'spain': 'Espanha',
    'cape verde': 'Cabo Verde', 'cabo verde': 'Cabo Verde',
    'uruguay': 'Uruguai',
    'saudi arabia': 'Arábia Saudita',
    'france': 'França',
    'iraq': 'Iraque',
    'norway': 'Noruega',
    'senegal': 'Senegal',
    'argentina': 'Argentina',
    'austria': 'Áustria',
    'algeria': 'Argélia',
    'jordan': 'Jordânia',
    'portugal': 'Portugal',
    'uzbekistan': 'Uzbequistão',
    'colombia': 'Colômbia',
    'congo dr': 'RD Congo', 'dr congo': 'RD Congo', 'congo democratic republic': 'RD Congo',
    'democratic republic of congo': 'RD Congo', 'congo': 'RD Congo',
    'england': 'Inglaterra',
    'croatia': 'Croácia',
    'ghana': 'Gana',
    'panama': 'Panamá',
}


# ============================================================
# CORREÇÕES MANUAIS DO ADMIN (Arthur)
# ============================================================
# Placares que VOCÊ define à mão e que VENCEM o openfootball pra todo mundo.
# Use quando o openfootball estiver errado ou atrasado.
# Formato: numero_do_jogo: [golsA, golsB]   (A e B na ordem oficial do bolão)
# Ex: o jogo 17 (Haiti x Brasil) foi 2x1 mas o openfootball lançou errado:
#     17: [2, 1],
# Quando o openfootball arrumar a fonte, é só apagar a linha daqui.
OVERRIDES = {
    # 17: [2, 1],
}


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(s.replace("'", ' ').split())


def canonical(name):
    return ALIASES.get(norm(name))


def build_index():
    """{ frozenset(timeA, timeB): (num, timeA_oficial, timeB_oficial) } para os 72 jogos."""
    idx = {}
    num = 1
    for teams in GROUPS.values():
        for a, b in PAIRS:
            ta, tb = teams[a], teams[b]
            idx[frozenset((ta, tb))] = (num, ta, tb)
            num += 1
    return idx


def extract_score(m):
    """Placar do tempo normal/prorrogação em vários formatos do openfootball."""
    sc = m.get('score')
    if isinstance(sc, dict):
        ft = sc.get('ft')
        if isinstance(ft, list) and len(ft) == 2 and all(x is not None for x in ft):
            return int(ft[0]), int(ft[1])
    if m.get('score1') is not None and m.get('score2') is not None:
        return int(m['score1']), int(m['score2'])
    return None


def main():
    req = urllib.request.Request(SOURCE, headers={'User-Agent': 'bolao-copa-2026'})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())

    idx = build_index()
    results = {}
    unmatched = []

    for m in data.get('matches', []):
        if not m.get('group'):  # só fase de grupos
            continue
        score = extract_score(m)
        if score is None:  # ainda não jogou
            continue
        ca, cb = canonical(m.get('team1', '')), canonical(m.get('team2', ''))
        if not ca:
            unmatched.append(m.get('team1'))
            continue
        if not cb:
            unmatched.append(m.get('team2'))
            continue
        hit = idx.get(frozenset((ca, cb)))
        if not hit:
            continue
        num, ta, tb = hit
        if ca == ta and cb == tb:
            results[str(num)] = [score[0], score[1]]
        else:  # openfootball listou na ordem inversa — espelha o placar
            results[str(num)] = [score[1], score[0]]

    if unmatched:
        print('AVISO — nomes não reconhecidos (adicione em ALIASES):',
              sorted(set(unmatched)), file=sys.stderr)

    # Correções do admin vencem o openfootball.
    for num, score in OVERRIDES.items():
        if (isinstance(score, list) and len(score) == 2
                and all(isinstance(x, int) and 0 <= x <= 20 for x in score)):
            results[str(num)] = list(score)
        else:
            print(f'AVISO — OVERRIDE inválido no jogo {num}: {score} (ignorado)',
                  file=sys.stderr)

    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, sort_keys=True)

    n_over = len([k for k in OVERRIDES])
    extra = f' ({n_over} correção(ões) manual(is) aplicada(s))' if n_over else ''
    print(f'{len(results)} jogos de grupos gravados em results.json{extra}')


if __name__ == '__main__':
    main()
