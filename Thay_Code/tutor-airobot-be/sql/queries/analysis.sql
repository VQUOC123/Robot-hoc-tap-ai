-- name: CreateAnalysis :one
INSERT INTO analyses (
    device_id, student_id, activity, focus_score, hw_visible,
    s1_doing_hw, s1_confidence, s1_latency_ms,
    s2_subject, s2_grade, s2_hw_type, s2_progress, s2_hints, s2_latency_ms,
    provider_id, image_path, image_width, image_height, image_size_kb
) VALUES (
    $1, $2, $3, $4, $5,
    $6, $7, $8,
    $9, $10, $11, $12, $13, $14,
    $15, $16, $17, $18, $19
) RETURNING *;

-- name: GetAnalysis :one
SELECT * FROM analyses WHERE id = $1 LIMIT 1;

-- name: ListAnalyses :many
SELECT * FROM analyses
WHERE ($1::uuid IS NULL OR device_id = $1)
  AND ($2::varchar IS NULL OR s2_subject = $2)
  AND ($3::boolean IS NULL OR s1_doing_hw = $3)
  AND ($4::timestamptz IS NULL OR created_at < $4)
ORDER BY created_at DESC
LIMIT $5;

-- name: CountAnalysesToday :one
SELECT COUNT(*) FROM analyses
WHERE created_at >= date_trunc('day', now());

-- name: CountHomeworkToday :one
SELECT COUNT(*) FROM analyses
WHERE created_at >= date_trunc('day', now())
  AND s1_doing_hw = true;

-- name: CountBySubject :many
SELECT s2_subject, COUNT(*) AS count
FROM analyses
WHERE created_at >= $1 AND created_at < $2
  AND s2_subject IS NOT NULL
GROUP BY s2_subject
ORDER BY count DESC;

-- name: AvgLatencyByProvider :many
SELECT
    provider_id,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY s1_latency_ms) AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s1_latency_ms) AS p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY s1_latency_ms) AS p99_ms
FROM analyses
WHERE created_at >= $1
  AND s1_latency_ms IS NOT NULL
  AND provider_id IS NOT NULL
GROUP BY provider_id;
