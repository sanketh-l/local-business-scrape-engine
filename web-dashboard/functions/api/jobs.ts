import { json, type Env } from './_utils';

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  const rows = await env.DB.prepare('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 20').all();
  return json({ jobs: rows.results || [] });
};
