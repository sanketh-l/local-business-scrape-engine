import { github, json, makeId, type Env } from './_utils';

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  try {
    if (!env.GITHUB_TOKEN) return json({ error: 'Missing GITHUB_TOKEN secret in Cloudflare.' }, 500);
    const body = await request.json<any>();
    if (body.real_scrape && !body.compliance_ack) {
      return json({ error: 'Real scraping requires compliance acknowledgement.' }, 400);
    }
    const jobId = makeId('job');
    await env.DB.prepare(
      `INSERT INTO jobs (id, city, country, area, category, coverage, max_areas, worker_limit, real_scrape, status, message)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'starting', 'GitHub workflow dispatch requested')`
    ).bind(
      jobId,
      String(body.city || 'Bengaluru'),
      String(body.country || 'India'),
      String(body.area || ''),
      String(body.category || 'plumber'),
      String(body.coverage || 'Street-level, many small squares'),
      Number(body.max_areas || 25),
      Number(body.worker_limit || 1),
      body.real_scrape ? 1 : 0,
    ).run();

    const origin = new URL(request.url).origin;
    const response = await github(env, '/actions/workflows/dashboard-run.yml/dispatches', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          city: String(body.city || 'Bengaluru'),
          country: String(body.country || 'India'),
          area: String(body.area || ''),
          category: String(body.category || 'plumber'),
          coverage: String(body.coverage || 'Street-level, many small squares'),
          max_areas: String(body.max_areas || 25),
          worker_limit: String(body.worker_limit || 1),
          real_scrape: body.real_scrape ? 'true' : 'false',
          compliance_ack: body.compliance_ack ? 'I_ACCEPT_LEGAL_RISK' : 'No',
          job_id: jobId,
          callback_url: origin,
        },
      }),
    });
    if (!response.ok) {
      const error = await response.text();
      await env.DB.prepare("UPDATE jobs SET status = 'failed', message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?").bind(error, jobId).run();
      return json({ error }, response.status);
    }
    return json({ job_id: jobId, message: 'Cloud job started. Watch live progress below.' });
  } catch (error: any) {
    return json({ error: error?.message || String(error) }, 500);
  }
};
