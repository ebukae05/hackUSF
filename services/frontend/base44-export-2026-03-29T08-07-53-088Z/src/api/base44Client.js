export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8080';

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const error = new Error(payload?.message || `Request failed with status ${response.status}`);
    error.status = response.status;
    error.data = payload;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export async function fetchDashboardState() {
  let lastError;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await request('/api/matches');
    } catch (error) {
      lastError = error;
      if (attempt === 0) {
        await sleep(2000);
      }
    }
  }

  throw lastError;
}

export async function runPipeline() {
  return request('/api/run-pipeline', { method: 'POST' });
}

export async function submitMatchDecision(matchId, decision) {
  return request(`/api/matches/${matchId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ decision }),
  });
}

export const db = {
  auth: {
    isAuthenticated: async () => true,
    me: async () => ({ role: 'operator', name: 'Demo Operator' }),
    logout: () => {},
    redirectToLogin: () => {},
  },
  entities: new Proxy(
    {},
    {
      get: () => ({
        list: async () => [],
        filter: async () => [],
        get: async () => null,
        create: async () => {
          throw new Error('This frontend is wired to the existing ReliefLink backend, which does not expose Base44 entity writes.');
        },
        update: async () => {
          throw new Error('This frontend is wired to the existing ReliefLink backend, which does not expose Base44 entity updates.');
        },
        delete: async () => {
          throw new Error('This frontend is wired to the existing ReliefLink backend, which does not expose Base44 entity deletes.');
        },
      }),
    }
  ),
  integrations: {
    Core: {
      UploadFile: async () => ({ file_url: '' }),
    },
  },
};

export const base44 = db;
export default db;
