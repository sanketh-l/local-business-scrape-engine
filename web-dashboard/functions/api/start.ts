import { github, json, type Env } from './_utils';

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  if (!env.GITHUB_TOKEN) return json({ error: 'Missing GITHUB_TOKEN secret in Cloudflare.' }, 500);
  const body = await request.json<any>();
  if (body.real_scrape && !body.compliance_ack) {
    return json({ error: 'Real scraping requires compliance acknowledgement.' }, 400);
  }
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
      },
    }),
  });
  if (!response.ok) return json({ error: await response.text() }, response.status);
  return json({ message: 'Cloud job started. Refresh status in a few seconds.' });
};
