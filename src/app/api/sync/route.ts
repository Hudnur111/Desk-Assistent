import { NextResponse } from 'next/server';
import { execSync } from 'child_process';

export async function POST() {
  try {
    const cwd = process.cwd();
    const output = execSync('git pull --ff-only origin main 2>&1', { cwd, timeout: 15000 }).toString();
    return NextResponse.json({ status: 'ok', output });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Sync failed';
    return NextResponse.json({ status: 'error', output: msg }, { status: 500 });
  }
}

export async function GET() {
  try {
    const cwd = process.cwd();
    const branch = execSync('git rev-parse --abbrev-ref HEAD 2>&1', { cwd }).toString().trim();
    const commit = execSync('git log -1 --format="%h %s" 2>&1', { cwd }).toString().trim();
    const status = execSync('git status --short 2>&1', { cwd }).toString().trim();
    return NextResponse.json({ branch, commit, dirty: status.length > 0, status });
  } catch (err: unknown) {
    return NextResponse.json({ error: err instanceof Error ? err.message : 'Git error' });
  }
}
