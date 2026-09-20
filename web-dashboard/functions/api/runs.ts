import { github, json, type Env } from './_utils';

export const onRequestGet: PagesFunction<Env> = async ({ env }) => {
  try {
    if (!env.GITHUB_TOKEN) return json({ runs: [] });
    const response = await github(env, '/actions/workflows/dashboard-run.yml/runs?per_page=10');
    if (!response.ok) return json({ runs: [] });
    const data: any = await response.json();
    return json({
      runs: (data.workflow_runs || []).map((run: any) => ({
        id: run.id,
        name: run.display_title || run.name,
        status: run.status,
        conclusion: run.conclusion,
        html_url: run.html_url,
        created_at: run.created_at,
      })),
    });
  } catch {
    return json({ runs: [] });
  }
};
