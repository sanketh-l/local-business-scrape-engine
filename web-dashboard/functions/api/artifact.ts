import { github, json, type Env } from './_utils';

export const onRequestGet: PagesFunction<Env> = async ({ request, env }) => {
  const runId = new URL(request.url).searchParams.get('run_id');
  if (!runId) return json({ error: 'run_id is required' }, 400);
  const artifactsResponse = await github(env, `/actions/runs/${runId}/artifacts`);
  if (!artifactsResponse.ok) return json({ error: await artifactsResponse.text() }, artifactsResponse.status);
  const artifacts: any = await artifactsResponse.json();
  const artifact = (artifacts.artifacts || []).find((item: any) => item.name === 'leadgen-dashboard-output') || artifacts.artifacts?.[0];
  if (!artifact) return json({ error: 'No artifact found for this run yet.' }, 404);
  const download = await github(env, `/actions/artifacts/${artifact.id}/zip`);
  if (!download.ok) return json({ error: await download.text() }, download.status);
  return new Response(download.body, {
    headers: {
      'content-type': 'application/zip',
      'content-disposition': `attachment; filename="${artifact.name}.zip"`,
    },
  });
};
