-- Classificação por temporada.
-- Grão: um clube em uma temporada.
-- Pontos: vitória = 3, empate = 1, derrota = 0.
-- Posição: maior pontuação primeiro; empate pelo saldo de gols.
WITH jogos AS (
    -- Grão: um clube em uma partida, com resultado do ponto de vista dele.
    SELECT
        temporada,
        mandante                                              AS clube,
        gols_mandante                                         AS gols_pro,
        gols_visitante                                        AS gols_contra,
        CASE resultado WHEN 'mandante' THEN 1 ELSE 0 END      AS vitoria,
        CASE resultado WHEN 'empate'   THEN 1 ELSE 0 END      AS empate,
        CASE resultado WHEN 'visitante' THEN 1 ELSE 0 END     AS derrota
    FROM refined.partidas
    UNION ALL
    SELECT
        temporada,
        visitante,
        gols_visitante,
        gols_mandante,
        CASE resultado WHEN 'visitante' THEN 1 ELSE 0 END,
        CASE resultado WHEN 'empate'    THEN 1 ELSE 0 END,
        CASE resultado WHEN 'mandante'  THEN 1 ELSE 0 END
    FROM refined.partidas
),
agregado AS (
    SELECT
        temporada,
        clube,
        count(*)        AS jogos,
        sum(vitoria)    AS vitorias,
        sum(empate)     AS empates,
        sum(derrota)    AS derrotas,
        sum(gols_pro)   AS gols_pro,
        sum(gols_contra) AS gols_contra,
        sum(gols_pro) - sum(gols_contra) AS saldo,
        sum(vitoria) * 3 + sum(empate)   AS pontos
    FROM jogos
    GROUP BY temporada, clube
)
SELECT
    temporada,
    clube,
    jogos,
    vitorias,
    empates,
    derrotas,
    gols_pro,
    gols_contra,
    saldo,
    pontos,
    rank() OVER (
        PARTITION BY temporada
        ORDER BY pontos DESC, saldo DESC, gols_pro DESC, clube
    ) AS posicao
FROM agregado
ORDER BY temporada, posicao