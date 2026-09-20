export type Env = {
  GITHUB_TOKEN: string;
  GITHUB_OWNER?: string;
  GITHUB_REPO?: string;
};

export function github(env: Env, path: string, init: RequestInit = {}) {
  const owner = env.GITHUB_OWNER || 'sanketh-l';
  const repo = env.GITHUB_REPO || 'local-business-scrape-engine';
  return fetch(`https://api.github.com/repos/${owner}/${repo}${path}`, {
    ...init,
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      'User-Agent': 'leadgen-cloudflare-dashboard',
      'X-GitHub-Api-Version': '2022-11-28',
      ...(init.headers || {}),
    },
  });
}

export function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}
