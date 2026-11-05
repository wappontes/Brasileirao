-- Média de gols por jogo, por temporada.
-- Grão: uma temporada.
-- Apenas partidas com gols_registrados = true.
-- Motivo: 2003 a 2013 não têm gols registrados para partidas com placar diferente de 0-0.
--         Sem o filtro, esses anos apareceriam com média artificialmente baixa.
SELECT
    p.temporada,
    count(DISTINCT g.partida_id)                   AS partidas_com_gol,
    count(*)                                       AS total_gols,
    round(count(*) * 1.0 / count(DISTINCT g.partida_id), 2) AS media_gols
FROM refined.gols       AS g
JOIN refined.partidas   AS p ON p.partida_id = g.partida_id
GROUP BY p.temporada
ORDER BY p.temporada