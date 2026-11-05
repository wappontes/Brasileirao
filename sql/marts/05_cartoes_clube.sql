-- Cartões por clube por temporada.
-- Grão: um clube em uma temporada.
-- Apenas partidas com cartoes_registrados = true.
-- Motivo: 2003 a 2013 não têm cartões registrados.
--         Incluir esses anos faria clubes aparecerem com zero cartões, o que é falso.
WITH base AS (
    SELECT
        p.temporada,
        c.clube,
        p.partida_id,
        count(*) FILTER (WHERE c.cartao = 'Amarelo') AS amarelos,
        count(*) FILTER (WHERE c.cartao = 'Vermelho') AS vermelhos
    FROM refined.cartoes    AS c
    JOIN refined.partidas   AS p ON p.partida_id = c.partida_id
    WHERE p.cartoes_registrados = true
    GROUP BY p.temporada, c.clube, p.partida_id
)
SELECT
    temporada,
    clube,
    count(DISTINCT partida_id)              AS partidas,
    sum(amarelos)                           AS amarelos,
    sum(vermelhos)                          AS vermelhos,
    round(sum(amarelos)  * 1.0 / count(DISTINCT partida_id), 2) AS amarelos_por_jogo,
    round(sum(vermelhos) * 1.0 / count(DISTINCT partida_id), 2) AS vermelhos_por_jogo
FROM base
GROUP BY temporada, clube
ORDER BY temporada, clube