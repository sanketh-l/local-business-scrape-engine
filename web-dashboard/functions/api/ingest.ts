import { json, makeId, type Env } from './_utils';

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  const auth = request.headers.get('authorization') || '';
  if (!env.INGEST_SECRET || auth !== `Bearer ${env.INGEST_SECRET}`) return json({ error: 'Unauthorized' }, 401);
  const body = await request.json<any>();
  const jobId = String(body.job_id || '');
  if (!jobId) return json({ error: 'job_id is required' }, 400);

  if (body.job) {
    await env.DB.prepare(
      `UPDATE jobs SET status = COALESCE(?, status), run_id = COALESCE(?, run_id), run_url = COALESCE(?, run_url),
       areas_total = COALESCE(?, areas_total), areas_completed = COALESCE(?, areas_completed),
       squares_total = COALESCE(?, squares_total), squares_completed = COALESCE(?, squares_completed),
       raw_rows = COALESCE(?, raw_rows), unique_businesses = COALESCE(?, unique_businesses),
       message = COALESCE(?, message), updated_at = CURRENT_TIMESTAMP WHERE id = ?`
    ).bind(
      body.job.status ?? null,
      body.job.run_id ?? null,
      body.job.run_url ?? null,
      body.job.areas_total ?? null,
      body.job.areas_completed ?? null,
      body.job.squares_total ?? null,
      body.job.squares_completed ?? null,
      body.job.raw_rows ?? null,
      body.job.unique_businesses ?? null,
      body.job.message ?? null,
      jobId,
    ).run();
  }

  for (const [index, area] of (body.areas || []).entries()) {
    await env.DB.prepare(
      `INSERT INTO job_areas (id, job_id, area_name, status, squares_total, squares_completed, raw_rows, unique_businesses, position)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(id) DO UPDATE SET status = excluded.status, squares_total = excluded.squares_total,
       squares_completed = excluded.squares_completed, raw_rows = excluded.raw_rows, unique_businesses = excluded.unique_businesses,
       updated_at = CURRENT_TIMESTAMP`
    ).bind(
      `${jobId}:${area.name}`,
      jobId,
      area.name,
      area.status || 'queued',
      area.squares_total || 0,
      area.squares_completed || 0,
      area.raw_rows || 0,
      area.unique_businesses || 0,
      area.position ?? index,
    ).run();
  }

  for (const lead of body.leads || []) {
    const id = lead.business_id || lead.place_id || lead.cid || makeId('lead');
    await env.DB.prepare(
      `INSERT OR REPLACE INTO leads
       (id, job_id, business_name, primary_category, phone, has_website, website, google_maps_link, address, city, region, country,
        latitude, longitude, rating, review_count, status, place_id, cid, source_keywords, source_grid_cells_count)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      `${jobId}:${id}`,
      jobId,
      lead.business_name || '',
      lead.primary_category || '',
      lead.phone || '',
      lead.has_website || (lead.website ? 'yes' : 'no'),
      lead.website || '',
      lead.google_maps_link || '',
      lead.address || '',
      lead.city || '',
      lead.region || '',
      lead.country || '',
      lead.latitude || null,
      lead.longitude || null,
      lead.rating || null,
      lead.review_count || null,
      lead.status || '',
      lead.place_id || '',
      lead.cid || '',
      lead.source_keywords || '',
      lead.source_grid_cells_count || 0,
    ).run();
  }
  return json({ ok: true });
};
