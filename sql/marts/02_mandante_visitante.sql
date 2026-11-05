-- Mandante x visitante por temporada.
-- Grão: uma temporada.
-- Confere se a vantagem do mandante mudou ao longo dos anos.
SELECT
    temporada,
    count(*)                                                                AS partidas,
    count(*) FILTER (WHERE resultado = 'mandante')                          AS vitorias_mandante,
    count(*) FILTER (WHERE resultado = 'empate')                            AS empates,
    count(*) FILTER (WHERE resultado = 'visitante')                         AS vitorias_visitante,
    round(100.0 * count(*) FILTER (WHERE resultado = 'mandante')
          / count(*), 1)                                                    AS pct_mandante,
    round(100.0 * count(*) FILTER (WHERE resultado = 'empate')
          / count(*), 1)                                                    AS pct_empate,
    round(100.0 * count(*) FILTER (WHERE resultado = 'visitante')
          / count(*), 1)                                                    AS pct_visitante
FROM refined.partidas
GROUP BY temporada
ORDER BY temporada