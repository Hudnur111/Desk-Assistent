// Skills Loader — loads skill definitions for both providers

export interface Skill {
  id: string;
  name: string;
  icon: string;
  systemPrompt: string;
  trigger: string;
  category: string;
  provider: 'ollama' | 'claude' | 'both';
}

export interface SkillsManifest {
  provider: string;
  version: string;
  skills: Omit<Skill, 'provider'>[];
}

const cache = new Map<string, Skill[]>();

export async function loadSkills(provider: 'ollama' | 'claude'): Promise<Skill[]> {
  if (cache.has(provider)) return cache.get(provider)!;

  try {
    const res = await fetch(`/skills/${provider}/index.json`);
    if (!res.ok) return [];
    const manifest: SkillsManifest = await res.json();
    const skills = manifest.skills.map((s) => ({ ...s, provider }));
    cache.set(provider, skills);
    return skills;
  } catch {
    return [];
  }
}

export async function getAllSkills(): Promise<Skill[]> {
  const [ollama, claude] = await Promise.all([
    loadSkills('ollama'),
    loadSkills('claude'),
  ]);
  return [...ollama, ...claude];
}
