import { type Env } from './_utils';

export const onRequestGet: PagesFunction<Env> = async ({ request, env }) => {
  const jobId = new URL(request.url).searchParams.get('job_id');
  if (!jobId) return new Response('job_id is required', { status: 400 });
  const rows = await env.DB.prepare('SELECT * FROM leads WHERE job_id = ? ORDER BY business_name').bind(jobId).all<any>();
  const headers = ['business_name','primary_category','phone','has_website','website','google_maps_link','address','city','region','country','latitude','longitude','rating','review_count','status','place_id','cid','source_keywords','source_grid_cells_count'];
  const escape = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const csv = [headers.join(','), ...(rows.results || []).map((row: any) => headers.map((header) => escape(row[header])).join(','))].join('\n');
  return new Response(csv, {
    headers: {
      'content-type': 'text/csv; charset=utf-8',
      'content-disposition': `attachment; filename="${jobId}-leads.csv"`,
    },
  });
};
