-- Posse média por clube por temporada.
-- Grão: um clube em uma temporada.
-- Apenas linhas com posse_bola não nulo.
-- Motivo: 2003 a 2013 e 2024 não têm dado de posse.
--         Incluí-los sem filtro daria média zero, que é falsa.
SELECT
    p.temporada,
    e.clube,
    count(*)                       AS partidas_com_posse,
    round(avg(e.posse_bola), 1)    AS posse_media
FROM refined.estatisticas   AS e
JOIN refined.partidas       AS p ON p.partida_id = e.partida_id
WHERE e.posse_bola IS NOT NULL
GROUP BY p.temporada, e.clube
ORDER BY p.temporada, e.clube