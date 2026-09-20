import { json, type Env } from './_utils';

export const onRequestGet: PagesFunction<Env> = async ({ request, env }) => {
  const jobId = new URL(request.url).searchParams.get('job_id');
  if (!jobId) return json({ error: 'job_id is required' }, 400);
  const job = await env.DB.prepare('SELECT * FROM jobs WHERE id = ?').bind(jobId).first();
  const areas = await env.DB.prepare('SELECT * FROM job_areas WHERE job_id = ? ORDER BY position, area_name').bind(jobId).all();
  const leads = await env.DB.prepare('SELECT * FROM leads WHERE job_id = ? ORDER BY created_at DESC LIMIT 500').bind(jobId).all();
  return json({ job, areas: areas.results || [], leads: leads.results || [] });
};
