#!/usr/bin/env python3
"""
Busca os placares da fase de grupos da Copa 2026 no openfootball (domínio público,
sem chave de API) e grava results.json no formato do bolão: { "num_do_jogo": [golsA, golsB] }.

- Casa cada jogo pelo PAR de seleções (independe da ordem em que o openfootball lista),
  e orienta o placar conforme a ordem A/B oficial do bolão.
- Nomes não reconhecidos são reportados no log (não quebram a execução) — basta
  adicionar o apelido em ALIASES e rodar de novo.
- Placar do MATA-MATA: usa o placar de 120 min (campo "et" se houve prorrogação,
  senão "ft"). Pênaltis NÃO entram no placar — só definem quem avança (campo "p").
  As entradas do mata-mata saem como [golsA, golsB, "A"|"B"] (3º = quem avança).

Grupos (1-72) funcionam sozinhos. Mata-mata (73-104) só é casado depois que você
fixar os confrontos em KO_FIXTURES (e os mesmos times no MATCHES do HTML). Enquanto
KO_FIXTURES estiver vazio, os jogos de mata-mata são ignorados — sem efeito.
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

# Conjunto de nomes canônicos válidos do bolão (pra validar os fixtures do mata-mata).
VALID_TEAMS = {t for teams in GROUPS.values() for t in teams}

# ============================================================
# CONFRONTOS DO MATA-MATA (você preenche a cada fase)
# ============================================================
# VAZIO até a fase de grupos acabar. Quando fixar o chaveamento no HTML (teamA/teamB
# dos jogos 73-104), ESPELHE aqui o mesmo confronto, na MESMA ordem A/B:
#   numero_do_jogo: ('Time A', 'Time B'),   # nomes canônicos do bolão (com acento)
# Ex (R32): 73: ('Brasil', 'Suíça'),
# Só inclua jogos cujos DOIS times já estão definidos. O robô só casa o que estiver aqui.
KO_FIXTURES = {
    73: ('África do Sul', 'Canadá'),
    74: ('Alemanha', 'Paraguai'),
    75: ('Holanda', 'Marrocos'),
    76: ('Brasil', 'Japão'),
    77: ('França', 'Suécia'),
    78: ('Costa do Marfim', 'Noruega'),
    79: ('México', 'Equador'),
    80: ('Inglaterra', 'RD Congo'),
    81: ('Estados Unidos', 'Bósnia'),
    82: ('Bélgica', 'Senegal'),
    83: ('Portugal', 'Croácia'),
    84: ('Espanha', 'Áustria'),
    85: ('Suíça', 'Argélia'),
    86: ('Argentina', 'Cabo Verde'),
    87: ('Colômbia', 'Gana'),
    88: ('Austrália', 'Egito'),
    # --- OITAVAS (R16) — adicionado 04/07, espelha o HTML ---
    89: ('Paraguai', 'França'),
    90: ('Canadá', 'Marrocos'),
    91: ('Portugal', 'Espanha'),
    92: ('Estados Unidos', 'Bélgica'),
    93: ('Brasil', 'Noruega'),
    94: ('México', 'Inglaterra'),
    95: ('Argentina', 'Egito'),
    96: ('Suíça', 'Colômbia'),
    # --- QUARTAS — adicionado 08/07, espelha o HTML ---
    97: ('França', 'Marrocos'),
    98: ('Espanha', 'Bélgica'),
    99: ('Noruega', 'Inglaterra'),
    100: ('Argentina', 'Suíça'),
}

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
# Grupos:     numero_do_jogo: [golsA, golsB]
# Mata-mata:  numero_do_jogo: [golsA, golsB, "A"|"B"]   (3º = quem avança; obrigatório no empate)
# A e B na ordem oficial do bolão.
# Ex: jogo 17 (Haiti x Brasil) foi 2x1 mas o openfootball lançou errado:  17: [2, 1],
# Ex: jogo 89 (oitava) foi 1x1 e o time A passou nos pênaltis:           89: [1, 1, "A"],
# Quando o openfootball arrumar a fonte, é só apagar a linha daqui.
OVERRIDES = {
    # 17: [2, 1],
}


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    s = s.replace('&', ' and ').replace("'", ' ')
    return ' '.join(s.split())


def canonical(name):
    return ALIASES.get(norm(name))


def build_index():
    """{ frozenset(timeA, timeB): (num, timeA_oficial, timeB_oficial) } para grupos (1-72)
    + os jogos de mata-mata já fixados em KO_FIXTURES."""
    idx = {}
    num = 1
    for teams in GROUPS.values():
        for a, b in PAIRS:
            ta, tb = teams[a], teams[b]
            idx[frozenset((ta, tb))] = (num, ta, tb)
            num += 1
    for gnum, pair in KO_FIXTURES.items():
        ta, tb = pair
        if ta not in VALID_TEAMS or tb not in VALID_TEAMS:
            print(f'AVISO — KO_FIXTURES jogo {gnum}: nome não reconhecido em {pair} '
                  f'(use o nome canônico do bolão, com acento)', file=sys.stderr)
            continue
        idx[frozenset((ta, tb))] = (int(gnum), ta, tb)
    return idx


def extract_score(m):
    """Placar de 120 min: prorrogação ('et') se houve, senão tempo normal ('ft').
    Jogos de grupo nunca têm 'et', então caem no 'ft' normalmente."""
    sc = m.get('score')
    if isinstance(sc, dict):
        for key in ('et', 'ft'):
            v = sc.get(key)
            if isinstance(v, list) and len(v) == 2 and all(x is not None for x in v):
                return int(v[0]), int(v[1])
    if m.get('score1') is not None and m.get('score2') is not None:
        return int(m['score1']), int(m['score2'])
    return None


def pen_winner(m):
    """Vencedor da disputa de pênaltis: 0 = time1 (openfootball), 1 = time2.
    None se não houve pênalti (campo 'p' ausente)."""
    sc = m.get('score')
    if isinstance(sc, dict):
        p = sc.get('p')
        if isinstance(p, list) and len(p) == 2 and all(x is not None for x in p):
            if int(p[0]) > int(p[1]):
                return 0
            if int(p[1]) > int(p[0]):
                return 1
    return None


def build_results(matches, idx):
    """Constrói {num: [a,b]} (grupos) / {num: [a,b,'A'|'B']} (mata-mata) a partir
    da lista de jogos do openfootball e do índice de confrontos. Retorna (results, unmatched)."""
    results = {}
    unmatched = []
    for m in matches:
        score = extract_score(m)
        if score is None:  # ainda não jogou
            continue
        is_group = bool(m.get('group'))
        ca, cb = canonical(m.get('team1', '')), canonical(m.get('team2', ''))
        if is_group:
            if not ca:
                unmatched.append(m.get('team1'))
                continue
            if not cb:
                unmatched.append(m.get('team2'))
                continue
        else:
            # Mata-mata: antes de definir os times o openfootball usa placeholders
            # ("Winner Group A" etc.) — esses não casam e são ignorados em silêncio.
            if not ca or not cb:
                continue
        hit = idx.get(frozenset((ca, cb)))
        if not hit:
            continue  # par não mapeado (mata-mata ainda não fixado em KO_FIXTURES, ou jogo irrelevante)
        num, ta, tb = hit
        inverted = not (ca == ta and cb == tb)  # openfootball listou na ordem inversa
        a_goals, b_goals = (score[1], score[0]) if inverted else (score[0], score[1])

        if num <= 72:
            results[str(num)] = [a_goals, b_goals]
        else:
            # Mata-mata: define quem avança.
            if a_goals > b_goals:
                adv = 'A'
            elif b_goals > a_goals:
                adv = 'B'
            else:
                pw = pen_winner(m)  # 0=time1, 1=time2 na ordem do openfootball
                if pw is None:
                    adv = None  # empate sem pênalti registrado ainda
                else:
                    pw_side = pw if not inverted else (1 - pw)  # reorienta pra A/B do bolão
                    adv = 'A' if pw_side == 0 else 'B'
            entry = [a_goals, b_goals] + ([adv] if adv else [])
            results[str(num)] = entry
    return results, unmatched


def main():
    req = urllib.request.Request(SOURCE, headers={'User-Agent': 'bolao-copa-2026'})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())

    idx = build_index()
    results, unmatched = build_results(data.get('matches', []), idx)

    if unmatched:
        print('AVISO — nomes não reconhecidos (adicione em ALIASES):',
              sorted(set(unmatched)), file=sys.stderr)

    # Correções do admin vencem o openfootball.
    for num, score in OVERRIDES.items():
        ok = (isinstance(score, list) and len(score) in (2, 3)
              and isinstance(score[0], int) and isinstance(score[1], int)
              and 0 <= score[0] <= 20 and 0 <= score[1] <= 20)
        if ok and len(score) == 3:
            ok = score[2] in ('A', 'B')
        if ok:
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


